""" This file contains all the settings for the application. """
import os
from dotenv import load_dotenv


load_dotenv()

DB_USER = "fastapi_user"
DB_PASSWORD = "your_password"
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "helpmeout"
DB_TYPE = "sqlite"
MEDIA_DIR = "./media"
VIDEO_DIR = f"{MEDIA_DIR}/uploads/"
COMPRESSED_DIR = f"{MEDIA_DIR}/compressed/"
THUMBNAIL_DIR = f"{MEDIA_DIR}/thumbnails/"
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URL = "https://cofucan.tech/srce/api/google/callback/"
