from django.shortcuts import render
from django.contrib import admin
from access.services.security_stats import get_security_dashboard_data
import json


def security_dashboard(request):
    days = int(request.GET.get("days", 7))
    if days not in (7, 30, 90):
        days = 7

    user_email = request.GET.get("user", "").strip() or None

    data = get_security_dashboard_data(days=days, user_email=user_email)

    context = {
        **admin.site.each_context(request),
        "title": "Огляд безпеки",
        "days": days,
        "user_email": user_email or "",
        "all_emails_json": json.dumps(data["all_emails"]),
        # line chart
        "labels":      json.dumps(data["labels"]),
        "login_data":  json.dumps(data["login_data"]),
        "logout_data": json.dumps(data["logout_data"]),
        "failed_data": json.dumps(data["failed_data"]),
        # IP bar chart
        "ip_labels": json.dumps(data["ip_labels"]),
        "ip_counts": json.dumps(data["ip_counts"]),
        # active users bar chart
        "user_labels": json.dumps(data["user_labels"]),
        "user_counts": json.dumps(data["user_counts"]),
        # heatmap + suspicious
        "heatmap":         json.dumps(data["heatmap"]),
        "suspicious_list": data["suspicious_list"],
        "user_rows":       data["user_rows"],
        # cards
        "total_logins":  data["total_logins"],
        "total_failed":  data["total_failed"],
        "total_logouts": data["total_logouts"],
        "unique_ips":    data["unique_ips"],
    }
    return render(request, "admin/security_dashboard.html", context)