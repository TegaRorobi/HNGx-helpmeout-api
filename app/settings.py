""" This file contains all the settings for the application. """
from configparser import ConfigParser
from fastapi_mail import ConnectionConfig

config = ConfigParser()
config.read("config.ini")

DEEPGRAM_API_KEY = config["deepgram"]["api_key"]


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

conf = ConnectionConfig(
    MAIL_USERNAME = "YourUsername",
    MAIL_PASSWORD = "strong_password",
    MAIL_FROM = "your@email.com",
    MAIL_PORT = 587,
    MAIL_SERVER = "your mail server",
    MAIL_TLS = True,
    MAIL_SSL = False,
    USE_CREDENTIALS = True
)
