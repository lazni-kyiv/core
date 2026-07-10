from django.db.models import Count
from django.db.models.functions import TruncDate
from access.models import LoginLog


def get_auth_chart_data():
    qs = (
        LoginLog.objects
        .annotate(day=TruncDate("created_at"))
        .values("day", "action")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    labels_set = sorted({row["day"] for row in qs})

    data = {
        "login": {},
        "logout": {},
        "failed": {}
    }

    for row in qs:
        data[row["action"]][row["day"]] = row["count"]

    return {
        "labels": [d.strftime("%Y-%m-%d") for d in labels_set],
        "login": [data["login"].get(d, 0) for d in labels_set],
        "logout": [data["logout"].get(d, 0) for d in labels_set],
        "failed": [data["failed"].get(d, 0) for d in labels_set],
    }