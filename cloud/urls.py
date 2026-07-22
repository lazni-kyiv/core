from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from pathlib import Path

from drf_spectacular.views import SpectacularAPIView
from .views import SiteAnalyticsView, BotAnalyticsView
from access.dashboard import auth_dashboard
from access.security_dashboard import security_dashboard
from cloud.views import VueAppView

BASE_DIR = Path(__file__).resolve().parent.parent

_original_get_urls = admin.site.__class__.get_urls

def _patched_get_urls(self):
    custom = [
        path("auth-dashboard/",     self.admin_view(auth_dashboard),     name="auth-dashboard"),
        path("security-dashboard/", self.admin_view(security_dashboard), name="security-dashboard"),
    ]
    return custom + _original_get_urls(self)

admin.site.__class__.get_urls = _patched_get_urls

urlpatterns = [
    path("tech/", admin.site.urls),

    path("v1/auth/",      include("access.urls")),
    path("v1/guests/",    include("guests.urls")),
    path("v1/services/",  include("services.urls")),
    path("v1/contracts/", include("dogovir.urls")),
    path("v1/bookings/",  include("bookings.urls")),

    path("v1/stats/site/", SiteAnalyticsView.as_view()),
    path("v1/stats/bot/",  BotAnalyticsView.as_view()),
]
