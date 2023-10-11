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
    MAIL_USERNAME = "helpmeout.hngx@gmail.com",
    MAIL_PASSWORD = "Helpmeout.HNGX",
    MAIL_FROM = "helpmeout.hngx@gmail.com",
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True
)
