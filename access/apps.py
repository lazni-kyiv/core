# access/apps.py
from django.apps import AppConfig


class CloudAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'access'
    label = 'access'
    verbose_name = 'Cloud Authentication'