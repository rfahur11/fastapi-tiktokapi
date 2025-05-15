import cv2
import hashlib
import tempfile
import os
import requests
from io import BytesIO
from fastapi import UploadFile
from typing import Tuple, Optional, Union, BinaryIO

from app.config import Settings

settings = Settings()

async def get_thumbnail(file_content: bytes, filename: str) -> Tuple[Optional[BytesIO], Optional[str]]:
    """Extract a thumbnail from a video file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
        temp_video.write(file_content)
        temp_video_path = temp_video.name
    
    cap = cv2.VideoCapture(temp_video_path)
    if not cap.isOpened():
        os.unlink(temp_video_path)
        return None, None
    
    ret, frame = cap.read()
    cap.release()
    os.unlink(temp_video_path)
    
    if not ret:
        return None, None
    
    _, img_encoded = cv2.imencode('.jpg', frame)
    img_bytes = BytesIO(img_encoded.tobytes())
    new_filename = os.path.splitext(filename)[0] + '.jpg'
    
    return img_bytes, new_filename

def get_signature(file: Union[BytesIO, bytes]) -> str:
    """Generate MD5 hash of a file for API signature verification."""
    hash_md5 = hashlib.md5()
    
    if isinstance(file, bytes):
        hash_md5.update(file)
    else:
        file.seek(0)
        for chunk in iter(lambda: file.read(4096), b''):
            hash_md5.update(chunk)
        file.seek(0)
    
    return hash_md5.hexdigest()

async def upload_video(advertiser_id: str, file_content: bytes, filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Upload a video to the TikTok API."""
    video_signature = get_signature(file_content)
    
    url = f"{settings.API_URL_SB}/file/video/ad/upload/"
    headers = {'Access-Token': settings.ACCESS_TOKEN_SB}
    
    file_obj = BytesIO(file_content)
    files = {'video_file': (filename, file_obj)}
    
    data = {
        'advertiser_id': advertiser_id,
        'file_name': filename,
        'upload_type': 'UPLOAD_BY_FILE',
        'video_signature': video_signature,
        'flaw_detect': 'true',
        'auto_fix_enabled': 'true',
        'auto_bind_enabled': 'true'
    }
    
    response = requests.post(url, headers=headers, files=files, data=data)
    
    if response.status_code != 200:
        return None, f'Error: {response.status_code}, {response.text}'
    
    response_json = response.json()
    if response_json.get('code') != 0:
        return None, f'API Error: {response_json.get("message")}'
    
    return response_json.get('data', [{}])[0].get('video_id', None), None

async def upload_image(advertiser_id: str, file_content: bytes, filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Upload an image (thumbnail) to the TikTok API."""
    # Extract thumbnail from video
    file_obj, new_filename = await get_thumbnail(file_content, filename)
    
    if not file_obj:
        return None, 'Failed to extract thumbnail from video'
    
    image_signature = get_signature(file_obj)
    file_obj.seek(0)
    
    url = f"{settings.API_URL_SB}/file/image/ad/upload/"
    headers = {'Access-Token': settings.ACCESS_TOKEN_SB}
    
    files = {'image_file': (new_filename, file_obj)}
    data = {
        'advertiser_id': advertiser_id,
        'file_name': new_filename,
        'image_signature': image_signature,
    }
    
    response = requests.post(url, headers=headers, files=files, data=data)
    
    if response.status_code != 200:
        return None, f'Error: {response.status_code}, {response.text}'
    
    response_json = response.json()
    if response_json.get('code') != 0:
        return None, f'API Error: {response_json.get("message")}'
    
    return response_json.get('data', {}).get('image_id', None), None

async def get_identity(advertiser_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Get TikTok user identity for the advertiser."""
    url = f"{settings.API_URL_SB}/identity/get/?advertiser_id={advertiser_id}&identity_type=TT_USER"
    headers = {'Access-Token': settings.ACCESS_TOKEN_SB}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return None, f'Error: {response.status_code}, {response.text}'
    
    response_json = response.json()
    if response_json.get('code') != 0:
        return None, f'API Error: {response_json.get("message")}'
    
    return response_json.get('data', {}).get('identity_list', [{}])[0].get('identity_id', None), None