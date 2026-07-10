from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict


def get_security_dashboard_data(days=7, user_email=None):
    from access.models import LoginLog

    since = timezone.now() - timedelta(days=days)
    logs = LoginLog.objects.filter(created_at__gte=since)

    if user_email:
        logs = logs.filter(email=user_email)

    # ── 1. Line chart: logins / logouts / failed per day ──────────────────
    daily = (
        logs.values("action", "created_at__date")
            .annotate(count=Count("id"))
            .order_by("created_at__date")
    )

    date_range = [
        (timezone.now() - timedelta(days=i)).date()
        for i in range(days - 1, -1, -1)
    ]
    labels = [d.strftime("%b %d") for d in date_range]

    buckets = {
        "login":  defaultdict(int),
        "logout": defaultdict(int),
        "failed": defaultdict(int),
    }
    for row in daily:
        action = row["action"]
        if action in buckets:
            buckets[action][row["created_at__date"]] += row["count"]

    login_data  = [buckets["login"][d]  for d in date_range]
    logout_data = [buckets["logout"][d] for d in date_range]
    failed_data = [buckets["failed"][d] for d in date_range]

    # ── 2. Failed attempts by IP ───────────────────────────────────────────
    failed_by_ip = (
        logs.filter(action="failed")
            .values("ip_address")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
    )
    ip_labels = [r["ip_address"] or "unknown" for r in failed_by_ip]
    ip_counts = [r["count"] for r in failed_by_ip]

    # ── 3. Most active users (always unfiltered for the switcher) ─────────
    active_users = (
        LoginLog.objects.filter(created_at__gte=since, action="login")
            .values("email")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
    )
    user_labels = [r["email"] for r in active_users]
    user_counts = [r["count"] for r in active_users]

    # ── 4. Suspicious IPs (5+ failed attempts) ────────────────────────────
    suspicious = (
        logs.filter(action="failed")
            .values("ip_address", "email")
            .annotate(attempts=Count("id"))
            .filter(attempts__gte=5)
            .order_by("-attempts")[:20]
    )
    suspicious_list = list(suspicious)

    # ── 5. Hourly heatmap (day of week × hour) ────────────────────────────
    hourly_raw = (
        logs.values("created_at__week_day", "created_at__hour")
            .annotate(count=Count("id"))
    )
    heatmap = [[0] * 24 for _ in range(7)]
    for row in hourly_raw:
        wd = (row["created_at__week_day"] - 2) % 7
        h  = row["created_at__hour"]
        heatmap[wd][h] += row["count"]

    # ── 6. Summary cards ──────────────────────────────────────────────────
    total_logins  = logs.filter(action="login").count()
    total_failed  = logs.filter(action="failed").count()
    total_logouts = logs.filter(action="logout").count()
    unique_ips    = logs.values("ip_address").distinct().count()

    # ── 7. All known emails for the dropdown ──────────────────────────────
    all_emails = list(
        LoginLog.objects.filter(created_at__gte=since)
            .values_list("email", flat=True)
            .distinct()
            .order_by("email")
    )

    # ── 8. Per-user summary table ─────────────────────────────────────────
    base = LoginLog.objects.filter(created_at__gte=since)

    unique_emails = list(
        base.values_list("email", flat=True).distinct().order_by("email")
    )

    from django.db.models import Q
    action_counts = (
        base.values("email", "action")
            .annotate(count=Count("id"))
    )
    # build {email: {action: count}}
    counts_map = {}
    for row in action_counts:
        counts_map.setdefault(row["email"], {})[row["action"]] = row["count"]

    # build {email: [distinct ips]}
    ip_map = {}
    for row in base.exclude(ip_address=None).values("email", "ip_address").distinct():
        ip_map.setdefault(row["email"], set()).add(row["ip_address"])

    user_rows = []
    for email in unique_emails:
        actions = counts_map.get(email, {})
        user_rows.append({
            "email":   email,
            "logins":  actions.get("login", 0),
            "logouts": actions.get("logout", 0),
            "failed":  actions.get("failed", 0),
            "ips":     sorted(ip_map.get(email, set())),
        })

    user_rows.sort(key=lambda r: r["logins"] + r["logouts"] + r["failed"], reverse=True)

    return {
        "days": days,
        "user_email": user_email,
        "all_emails": all_emails,
        "user_rows": user_rows,
        "labels": labels,
        "login_data":  login_data,
        "logout_data": logout_data,
        "failed_data": failed_data,
        "ip_labels": ip_labels,
        "ip_counts": ip_counts,
        "user_labels": user_labels,
        "user_counts": user_counts,
        "suspicious_list": suspicious_list,
        "heatmap": heatmap,
        "total_logins":  total_logins,
        "total_failed":  total_failed,
        "total_logouts": total_logouts,
        "unique_ips":    unique_ips,
    }