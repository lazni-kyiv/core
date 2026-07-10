from django.urls import path
from .views import services_get

urlpatterns = [
    path("", services_get),
]
