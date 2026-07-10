from django.shortcuts import render
from django.contrib import admin
from access.services.auth_stats import get_auth_chart_data

def auth_dashboard(request):
    chart = get_auth_chart_data()
    context = {
        **admin.site.each_context(request),
        "labels": chart["labels"],
        "login_data": chart["login"],
        "logout_data": chart["logout"],
        "failed_data": chart["failed"],
    }
    return render(request, "admin/auth_dashboard.html", context)