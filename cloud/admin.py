from django.contrib import admin
from unfold.admin import ModelAdmin
from django.shortcuts import redirect
from unfold.decorators import action
from django.db import models
from .models import SystemConfig
from .models import RequestLog

@admin.register(SystemConfig)
class SystemConfigAdmin(ModelAdmin):
    list_display = ("site_stats_api_key", "bot_stats_api_key")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SystemConfig.get_solo()
        return redirect(f"{obj.pk}/change/")

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
from unfold.admin import ModelAdmin
from .models import RequestLog

@admin.register(RequestLog)
class RequestLogAdmin(ModelAdmin):
    list_display = ('method_badge', 'path', 'status_badge', 'response_time_badge', 'ip_address', 'user', 'created_at')
    list_filter = ('method', 'status_code')
    search_fields = ('path', 'ip_address', 'user__email')
    readonly_fields = ('method', 'path', 'status_code', 'response_time_ms', 'ip_address', 'user', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path('analytics/', self.admin_site.admin_view(self.analytics_view), name='requestlog_analytics'),
        ]
        return custom + urls

    def analytics_view(self, request):
        from django.shortcuts import render
        import json

        days = int(request.GET.get('days', 7))
        now = timezone.now()
        since = now - timedelta(days=days)

        qs = RequestLog.objects.filter(created_at__gte=since)

        # ── stat cards ──
        total = qs.count()
        errors = qs.filter(status_code__gte=400).count()
        avg_time = qs.aggregate(avg=Avg('response_time_ms'))['avg'] or 0
        slow = qs.filter(response_time_ms__gte=1000).count()

        # ── requests by day ──
        from django.db.models.functions import TruncDate
        by_day = (
            qs.annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                total=Count('id'),
                errors=Count('id', filter=models.Q(status_code__gte=400)),
                slow=Count('id', filter=models.Q(response_time_ms__gte=1000)),
            )
            .order_by('date')
        )
        labels      = [str(r['date']) for r in by_day]
        total_data  = [r['total']  for r in by_day]
        error_data  = [r['errors'] for r in by_day]
        slow_data   = [r['slow']   for r in by_day]

        # ── requests by hour (last 24h) ──
        qs_24h = RequestLog.objects.filter(created_at__gte=now - timedelta(hours=24))
        from django.db.models.functions import ExtractHour
        by_hour = (
            qs_24h.annotate(hour=ExtractHour('created_at'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
        )
        hour_map = {r['hour']: r['count'] for r in by_hour}
        hour_labels = [f"{str(h).zfill(2)}:00" for h in range(24)]
        hour_data   = [hour_map.get(h, 0) for h in range(24)]

        # ── top paths ──
        top_paths = (
            qs.values('path')
            .annotate(
                count=Count('id'),
                errors=Count('id', filter=models.Q(status_code__gte=400)),
                avg_ms=Avg('response_time_ms'),
            )
            .order_by('-count')[:10]
        )

        # ── method breakdown ──
        by_method = (
            qs.values('method')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        method_labels = [r['method'] for r in by_method]
        method_counts = [r['count']  for r in by_method]

        # ── status breakdown ──
        status_groups = {
            '2xx': qs.filter(status_code__gte=200, status_code__lt=300).count(),
            '3xx': qs.filter(status_code__gte=300, status_code__lt=400).count(),
            '4xx': qs.filter(status_code__gte=400, status_code__lt=500).count(),
            '5xx': qs.filter(status_code__gte=500).count(),
        }

        # ── top errors ──
        top_errors = (
            qs.filter(status_code__gte=400)
            .values('path', 'status_code')
            .annotate(count=Count('id'))
            .order_by('-count')[:8]
        )

        # ── slowest endpoints ──
        slowest = (
            qs.values('path')
            .annotate(avg_ms=Avg('response_time_ms'), count=Count('id'))
            .filter(count__gte=3)
            .order_by('-avg_ms')[:8]
        )

        # ── top IPs ──
        top_ips = (
            qs.values('ip_address')
            .annotate(count=Count('id'))
            .order_by('-count')[:8]
        )

        context = {
            **self.admin_site.each_context(request),
            'title': 'Request Analytics',
            'days': days,
            'total_requests': total,
            'error_count': errors,
            'error_rate': round((errors / total * 100) if total else 0, 1),
            'avg_response_time': round(avg_time),
            'slow_requests': slow,
            'labels':       json.dumps(labels),
            'total_data':   json.dumps(total_data),
            'error_data':   json.dumps(error_data),
            'slow_data':    json.dumps(slow_data),
            'hour_labels':  json.dumps(hour_labels),
            'hour_data':    json.dumps(hour_data),
            'method_labels': json.dumps(method_labels),
            'method_counts': json.dumps(method_counts),
            'status_groups': status_groups,
            'top_paths':    top_paths,
            'top_errors':   top_errors,
            'slowest':      slowest,
            'top_ips':      top_ips,
        }
        return render(request, 'admin/requestlog_analytics.html', context)

    # добавь кнопку в тулбар
    actions_list = ['go_to_analytics']

    @action(description='Analytics')
    def go_to_analytics(self, request):
        from django.shortcuts import redirect
        return redirect('../analytics/')

    def method_badge(self, obj):
        colors = {
            'GET':    ('#E1F5EE', '#085041'),
            'POST':   ('#EEF2FF', '#3730A3'),
            'PUT':    ('#FAEEDA', '#633806'),
            'PATCH':  ('#FEF9C3', '#854D0E'),
            'DELETE': ('#FCEBEB', '#791F1F'),
        }
        bg, fg = colors.get(obj.method, ('#F1EFE8', '#444441'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;'
            'border-radius:999px;font-size:12px;font-weight:500">{}</span>',
            bg, fg, obj.method,
        )
    method_badge.short_description = 'Method'

    def status_badge(self, obj):
        if obj.status_code < 300:
            bg, fg = '#E1F5EE', '#085041'
        elif obj.status_code < 400:
            bg, fg = '#FEF9C3', '#854D0E'
        elif obj.status_code < 500:
            bg, fg = '#FAEEDA', '#633806'
        else:
            bg, fg = '#FCEBEB', '#791F1F'
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;'
            'border-radius:999px;font-size:12px;font-weight:500">{}</span>',
            bg, fg, obj.status_code,
        )
    status_badge.short_description = 'Status'

    def response_time_badge(self, obj):
        if obj.response_time_ms < 200:
            color = '#085041'
        elif obj.response_time_ms < 1000:
            color = '#633806'
        else:
            color = '#791F1F'
        return format_html(
            '<span style="color:{};font-weight:500">{}ms</span>',
            color, obj.response_time_ms,
        )
    response_time_badge.short_description = 'Response time'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        return super().changelist_view(request, extra_context=extra_context)