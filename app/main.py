from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import socketio
from typing import Optional, Dict, Any, List
import json
import urllib.parse
from datetime import datetime
import os
from pathlib import Path

from app.config import Settings
from app.utils.auth_utils import generate_csrf_state, get_latest_token
from app.utils.api_utils import make_api_request
from app.utils.file_utils import upload_video, upload_image, get_identity
from app.utils.fuzzy_logic import FuzzyRanking
from app.models import FuzzyRankingRequest, FuzzyRankingResponse, RankedAdItem

# Load environment variables
settings = Settings()

# Initialize FastAPI app
app = FastAPI(title="TikTok Business API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Find the absolute path to the static directory
BASE_PATH = Path(__file__).resolve().parent
STATIC_PATH = BASE_PATH / "static"

# Socket.IO setup
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio)
app.mount("/socket.io", socket_app)

@sio.event
async def connect(sid, environ):
    print('Client connected', sid)

@sio.event
async def disconnect(sid):
    print('Client disconnected', sid)

# Setup static files and templates
app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")
templates = Jinja2Templates(directory=str(BASE_PATH / "templates"))

# Initialize FuzzyRanking
fuzzy_ranking = FuzzyRanking()

# Routes
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/oauth")
async def oauth_url():
    state = generate_csrf_state()
    auth_url = f"https://business-api.tiktok.com/portal/auth?app_id={settings.APP_ID}&state={state}&redirect_uri={settings.REDIRECT_URI}"
    # Instead of redirecting, return HTML that does the redirect for us
    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Redirecting to TikTok OAuth</title>
            <meta http-equiv="refresh" content="0;url={auth_url}">
        </head>
        <body>
            <p>Redirecting to TikTok OAuth...</p>
            <script>
                window.location.href = "{auth_url}";
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/callback")
async def callback(data: Dict[str, str]):
    full_url = data.get('url')
    if not full_url:
        raise HTTPException(status_code=400, detail="Missing URL in request")

    query_params = urllib.parse.parse_qs(urllib.parse.urlparse(full_url).query)
    auth_code = query_params.get('auth_code', [None])[0]
    state = query_params.get('state', [None])[0]

    if not auth_code or not state:
        raise HTTPException(status_code=400, detail="Invalid state or missing code")

    token_data = {'secret': settings.SECRET, 'app_id': settings.APP_ID, 'auth_code': auth_code}
    token_response, error = await make_api_request(f"{settings.API_URL}/oauth2/access_token/", json_data=token_data, method='POST')
    if error:
        raise HTTPException(status_code=400, detail=f"Failed to get access token: {error}")

    access_token = token_response['data']['access_token']
    from app.utils.auth_utils import redis_client
    redis_client.set(f'access_token:{state}', access_token)
    await sio.emit('token_update', {'access_token': access_token})
    return {"success": True}

@app.get("/get_advertiser")
async def get_advertiser():
    access_token = get_latest_token()
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token found")

    advertiser_url = f"{settings.API_URL}/oauth2/advertiser/get/?secret={settings.SECRET}&app_id={settings.APP_ID}"
    headers = {'Access-Token': access_token}
    advertiser_response, error = await make_api_request(advertiser_url, headers=headers)
    if error:
        raise HTTPException(status_code=400, detail=f"Failed to get advertiser: {error}")

    advertiser_ids = [item['advertiser_id'] for item in advertiser_response['data']['list']]
    if not advertiser_ids:
        return {"advertiser_ids": None}

    info_url = f"{settings.API_URL}/advertiser/info/?advertiser_ids={json.dumps(advertiser_ids)}"
    info_response, error = await make_api_request(info_url, headers=headers)
    if error:
        raise HTTPException(status_code=400, detail=f"Failed to get advertiser info: {error}")

    filtered_data = [{'id': item['advertiser_id'], 'name': item['name']} for item in info_response['data']['list']]
    return {"message": "OK", "data": filtered_data}

@app.post("/campaign")
async def create_campaign(data: Dict[str, Any]):
    campaign_data = {
        'advertiser_id': settings.ADVERTISER_ID_SB,
        'campaign_name': data.get('campaign_name'),
        'objective_type': 'TRAFFIC',
        'budget_mode': 'BUDGET_MODE_TOTAL',
        'budget': data.get('campaign_budget')
    }
    campaign_response, error = await make_api_request(
        f"{settings.API_URL_SB}/campaign/create/", 
        headers={'Access-Token': settings.ACCESS_TOKEN_SB}, 
        json_data=campaign_data, 
        method='POST'
    )
    if error:
        # Return a JSON response with the error instead of raising an HTTPException
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": error.get("message", str(error))}
        )
    return {"success": True}

@app.get("/campaign")
async def get_campaigns():
    campaign_url = f"{settings.API_URL_SB}/campaign/get/?advertiser_id={settings.ADVERTISER_ID_SB}"
    campaign_response, error = await make_api_request(
        campaign_url, 
        headers={'Access-Token': settings.ACCESS_TOKEN_SB}
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    filtered_data = [
        {
            'advertiser_id': item['advertiser_id'], 
            'id': item['campaign_id'], 
            'name': f"{item['campaign_name']} (Rp.{int(item['budget'])})"
        } 
        for item in campaign_response['data']['list'] 
        if item['operation_status'] == 'ENABLE'
    ]
    return {"message": "OK", "data": filtered_data}

@app.post("/ad_group")
async def create_ad_group(data: Dict[str, Any]):
    ad_group_data = {
        'advertiser_id': settings.ADVERTISER_ID_SB,
        'campaign_id': data.get('campaign_id'),
        'adgroup_name': data.get('ad_group_name'),
        'promotion_type': 'WEBSITE',
        'placement_type': 'PLACEMENT_TYPE_NORMAL',
        'placements': ['PLACEMENT_TIKTOK'],
        'location_ids': ['3932488'],
        'gender': 'GENDER_UNLIMITED',
        'operating_systems': ['ANDROID'],
        'budget_mode': 'BUDGET_MODE_DAY',
        'budget': data.get('ad_group_budget'),
        'schedule_type': 'SCHEDULE_FROM_NOW',
        'schedule_start_time': f'{datetime.now()}',
        'optimization_goal': 'CLICK',
        'bid_type': 'BID_TYPE_NO_BID',
        'billing_event': 'CPC',
        'pacing': 'PACING_MODE_SMOOTH',
        'operation_status': 'ENABLE'
    }
    ad_group_response, error = await make_api_request(
        f"{settings.API_URL_SB}/adgroup/create/", 
        headers={'Access-Token': settings.ACCESS_TOKEN_SB}, 
        json_data=ad_group_data, 
        method='POST'
    )
    if error:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": error.get("message", str(error))}
        )
    return {"success": True}

@app.get("/ad_group")
async def get_ad_groups(filtering: Optional[str] = None):
    ad_group_url = f"{settings.API_URL_SB}/adgroup/get/?advertiser_id={settings.ADVERTISER_ID_SB}"
    if filtering:
        ad_group_url += f"&filtering={filtering}"
    
    ad_group_response, error = await make_api_request(
        ad_group_url, 
        headers={'Access-Token': settings.ACCESS_TOKEN_SB}
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    filtered_data = [
        {
            'advertiser_id': item['advertiser_id'], 
            'campaign_id': item['campaign_id'], 
            'id': item['adgroup_id'], 
            'name': f"{item['adgroup_name']} (Rp.{int(item['budget'])})"
        } 
        for item in ad_group_response['data']['list'] 
        if item['operation_status'] == 'ENABLE'
    ]
    return {"message": "OK", "data": filtered_data}

@app.post("/ad")
async def create_ad(
    advertiser_id: str = Form(...),
    campaign_id: str = Form(...),
    ad_group_id: str = Form(...),
    ad_name: str = Form(...),
    ad_file: UploadFile = File(...)
):
    # Read file content
    file_content = await ad_file.read()
    
    # Upload image and video
    image_id, error = await upload_image(settings.ADVERTISER_ID_SB, file_content, ad_file.filename)
    if error:
        raise HTTPException(status_code=400, detail=error)
        
    video_id, error = await upload_video(settings.ADVERTISER_ID_SB, file_content, ad_file.filename)
    if error:
        raise HTTPException(status_code=400, detail=error)
        
    identity_id, error = await get_identity(settings.ADVERTISER_ID_SB)
    if error:
        raise HTTPException(status_code=400, detail=error)
        
    ad_data = {
        'advertiser_id': settings.ADVERTISER_ID_SB,
        'adgroup_id': ad_group_id,
        'creatives': [{
            'ad_name': ad_name,
            'identity_type': 'TT_USER',
            'identity_id': identity_id,
            'ad_format': 'SINGLE_VIDEO',
            'video_id': video_id,
            'image_ids': [image_id],
            'ad_text': 'Check out our new product!',
            'call_to_action': 'LEARN_MORE',
            'landing_page_url': 'https://example.com'
        }]
    }
    
    ad_response, error = await make_api_request(
        f"{settings.API_URL_SB}/ad/create/", 
        headers={'Access-Token': settings.ACCESS_TOKEN_SB}, 
        json_data=ad_data, 
        method='POST'
    )
    if error:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": error.get("message", str(error))}
        )
    
    return {"success": True}

@app.get("/report/{type}")
async def get_report(
    type: str,
    advertiser_id: str,
    date_range: str = "lifetime",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    access_token = get_latest_token()
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token found")
    
    type_config = {
        'ad': {
            'detail_endpoint': '/ad/get/',
            'detail_fields': ["ad_id", "ad_name", "adgroup_id", "adgroup_name", "campaign_id", "campaign_name"],
            'report_dimension': "ad_id",
            'data_level': "AUCTION_AD"
        },
        'adgroup': {
            'detail_endpoint': '/adgroup/get/',
            'detail_fields': ["adgroup_id", "adgroup_name", "campaign_id", "campaign_name"],
            'report_dimension': "adgroup_id",
            'data_level': "AUCTION_ADGROUP"
        },
        'campaign': {
            'detail_endpoint': '/campaign/get/',
            'detail_fields': ["campaign_id", "campaign_name"],
            'report_dimension': "campaign_id",
            'data_level': "AUCTION_CAMPAIGN"
        }
    }
    
    if type not in type_config:
        raise HTTPException(status_code=400, detail="Invalid report type")
        
    config = type_config[type]
    detail_url = f"{settings.API_URL}{config['detail_endpoint']}?advertiser_id={advertiser_id}&fields={json.dumps(config['detail_fields'])}&page_size=1000"
    detail_response, error = await make_api_request(detail_url, headers={'Access-Token': access_token})
    
    if error:
        raise HTTPException(status_code=400, detail=error)
        
    # Build the base report URL
    report_url = f"{settings.API_URL}/report/integrated/get/?advertiser_id={advertiser_id}&metrics=[\"impressions\",\"clicks\",\"conversion\",\"spend\",\"ctr\",\"conversion_rate\",\"cpc\"]&data_level={config['data_level']}&report_type=BASIC&dimensions=[\"{config['report_dimension']}\"]"
    
    # Add date parameters based on the requested date range type
    if date_range == 'lifetime':
        report_url += "&query_lifetime=true"
    elif date_range == 'custom' and start_date and end_date:
        report_url += f"&start_date={start_date}&end_date={end_date}"
    else:
        # Default to lifetime if parameters are invalid
        report_url += "&query_lifetime=true"
    
    # Add pagination
    report_url += "&page_size=1000"
    
    report_response, error = await make_api_request(report_url, headers={'Access-Token': access_token})
    
    if error:
        raise HTTPException(status_code=400, detail=error)
        
    detail_dict = {item[config['report_dimension']]: item for item in detail_response['data']['list']}
    merged_data = [
        {**report_item['dimensions'], **report_item['metrics'], **detail_dict[report_item['dimensions'][config['report_dimension']]]}
        for report_item in report_response['data']['list']
        if report_item['dimensions'][config['report_dimension']] in detail_dict
    ]
    
    # Include date range info in the response
    response_data = {
        'message': 'OK',
        'date_range': {
            'type': date_range,
            'start_date': start_date if date_range == 'custom' else None,
            'end_date': end_date if date_range == 'custom' else None
        },
        'data': merged_data
    }
    
    return response_data

@app.post("/rank-ads", response_model=FuzzyRankingResponse)
async def rank_ads(request: FuzzyRankingRequest):
    """
    Endpoint untuk melakukan ranking iklan menggunakan logika fuzzy
    """
    try:
        # Konversi dari Pydantic model ke list of dict
        data = [
            {
                "name": item.name,
                "cost": item.cost,
                "impressions": item.impressions,
                "clicks": item.clicks
            } for item in request.ads
        ]
        
        # Proses ranking
        ranked_data = fuzzy_ranking.rank_ads(data)
        
        # Konversi hasil ke format yang diinginkan
        result = {
            "ranked_ads": [
                RankedAdItem(
                    name=item.get("name", ""),
                    cost=item.get("cost", 0),
                    impressions=item.get("impressions", 0),
                    clicks=item.get("clicks", 0),
                    ranking=item.get("ranking", 0),
                    cost_norm=item.get("cost_norm", 0),
                    impressions_norm=item.get("impressions_norm", 0),
                    clicks_norm=item.get("clicks_norm", 0)
                ) for item in ranked_data
            ]
        }
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ranking ads: {str(e)}")

@app.post("/analyze-campaign")
async def analyze_campaign(advertiser_id: str, campaign_id: Optional[str] = None):
    """
    Endpoint untuk menganalisis performa kampanye menggunakan logika fuzzy
    """
    try:
        # Dapatkan data laporan dari API TikTok
        access_token = get_latest_token()
        if not access_token:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "No access token found"}
            )
        
        # Tentukan level data yang akan dianalisis
        level = "ad" if campaign_id else "campaign"
        
        # Base URL untuk laporan
        report_url = f"{settings.API_URL}/report/integrated/get/"
        
        # Buat parameter query sebagai dictionary
        params = {
            "advertiser_id": advertiser_id,
            "report_type": "BASIC",
            "metrics": json.dumps(["impressions", "clicks", "conversion", "spend", "ctr", "conversion_rate", "cpc"]),
            "query_lifetime": "true",
            "page_size": "1000"
        }
        
        if campaign_id:
            # Tambahkan parameter untuk level data dan dimensi
            params["data_level"] = "AUCTION_AD"
            params["dimensions"] = json.dumps(["ad_id"])
            
            # Tambahkan filter campaign_id dengan format yang benar
            filter_obj = {"campaign_ids": [campaign_id]}
            params["filtering"] = json.dumps(filter_obj)
        else:
            # Untuk level campaign
            params["data_level"] = "AUCTION_CAMPAIGN"
            params["dimensions"] = json.dumps(["campaign_id"])
        
        # Buat URL dengan parameter
        query_string = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
        final_url = f"{report_url}?{query_string}"
        
        # Debugging - print URL
        print(f"DEBUG - Report URL: {final_url}")
        
        # Dapatkan laporan dari API TikTok
        report_response, error = await make_api_request(final_url, headers={'Access-Token': access_token})
        if error:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Failed to get report: {error}"}
            )
        
        # Ekstrak data yang diperlukan untuk ranking fuzzy
        items = []
        for item in report_response.get('data', {}).get('list', []):
            metrics = item.get('metrics', {})
            dimensions = item.get('dimensions', {})
            
            ad_data = {
                "name": dimensions.get("ad_id" if level == "ad" else "campaign_id", "Unknown"),
                "cost": float(metrics.get("spend", 0)),
                "impressions": int(metrics.get("impressions", 0)),
                "clicks": int(metrics.get("clicks", 0))
            }
            items.append(ad_data)
        
        # Proses ranking dengan fuzzy logic
        ranked_items = fuzzy_ranking.rank_ads(items)
        
        # Return hasil ranking
        return {
            "success": True,
            "level": level,
            "campaign_id": campaign_id,
            "ranked_items": ranked_items
        }
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error analyzing campaign: {str(e)}", "traceback": traceback.format_exc()}
        )

@app.get("/get_latest_token")
async def get_latest_token_route():
    access_token = get_latest_token()
    return {"access_token": access_token}

