import requests
from typing import Dict, Any, Tuple, Optional

async def make_api_request(url: str, headers: Optional[Dict[str, str]] = None, json_data: Optional[Dict[str, Any]] = None, method: str = 'GET') -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        else:
            response = requests.post(url, headers=headers, json=json_data)
        
        response_json = response.json()
        if response_json.get('code') != 0:
            return None, response_json
        
        return response_json, None
    except Exception as e:
        return None, {"error": str(e), "message": str(e)}