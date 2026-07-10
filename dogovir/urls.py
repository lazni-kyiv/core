from django.urls import path

from .views import get_dogovir_text,contracts
urlpatterns = [
    path("template/", get_dogovir_text, name="dogovir-text"),
    path("",      contracts,   name="dogovir-list"),
]