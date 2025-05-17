from pydantic_settings import BaseSettings
import os
# from dotenv import load_dotenv

# load_dotenv()

class Settings(BaseSettings):
    APP_ID: str = os.getenv('APP_ID', '')
    SECRET: str = os.getenv('SECRET', '')
    REDIRECT_URI: str = os.getenv('REDIRECT_URI', '')
    ACCESS_TOKEN_SB: str = os.getenv('ACCESS_TOKEN_SB', '')
    ADVERTISER_ID_SB: str = os.getenv('ADVERTISER_ID_SB', '')
    API_URL: str = 'https://business-api.tiktok.com/open_api/v1.3'
    API_URL_SB: str = 'https://sandbox-ads.tiktok.com/open_api/v1.3'

    class Config:
        env_file = ".env"