# cloud/settings/stage.py

from .base import *
import os

DEBUG = False

SECRET_KEY = os.getenv("SECRET_KEY")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": "127.0.0.1",
        "PORT": "3306",
    }
}

CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_HOSTS", "").split(",")

UNFOLD["ENVIRONMENT"] = ["STAGE", "warning"]