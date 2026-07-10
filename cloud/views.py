import requests
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .models import SystemConfig


def fetch_external(url, token):
    try:
        res = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}"
            },
            timeout=5
        )

        if res.status_code != 200:
            return None, res.status_code

        return res.json(), 200

    except requests.RequestException:
        return None, 500


# =====================
# SITE STATS
# =====================

class SiteAnalyticsView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        config = SystemConfig.get_solo()

        data, status = fetch_external(
            "https://laznikyiv.com/api/stats",
            config.site_stats_api_key
        )

        if not data:
            return JsonResponse({"error": "Upstream error"}, status=status)

        return JsonResponse(data, safe=False)


# =====================
# BOT STATS
# =====================

class BotAnalyticsView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        config = SystemConfig.get_solo()

        data, status = fetch_external(
            "https://bot.laznikyiv.com/api/stats",
            config.bot_stats_api_key
        )

        if not data:
            return JsonResponse({"error": "Upstream error"}, status=status)

        return JsonResponse(data, safe=False)

# cloud/views.py

from django.views.generic import TemplateView


class VueAppView(TemplateView):
    template_name = "index.html"