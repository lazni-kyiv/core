from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import requests

# ✏️  Change this import to match your actual app and model
from bookings.models import Booking


# ---------------------------------------------------------------
# ✏️  Set these in your settings.py or .env and load them here:
#     TELEGRAM_BOT_TOKEN = "123456:ABC-your-token"
#     TELEGRAM_CHAT_ID   = "1071137580"
# ---------------------------------------------------------------
from django.conf import settings

TELEGRAM_BOT_TOKEN ="8133338898:AAG70Ve1R1qusRS_28WjGa0J4a1_KFXxSsI"
TELEGRAM_CHAT_ID   = "1071137580"

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def send_telegram_message(text: str) -> bool:
    """Send a message via Telegram bot. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    try:
        response = requests.post(
            TELEGRAM_API_URL,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("ok", False)
    except requests.RequestException:
        return False


class Command(BaseCommand):
    help = "List bookings starting within the next hour and notify via Telegram"

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=60,
            help="Look-ahead window in minutes (default: 60)",
        )
        parser.add_argument(
            "--no-telegram",
            action="store_true",
            help="Skip Telegram notifications (print to console only)",
        )

    def handle(self, *args, **options):
        now    = timezone.now()
        soon   = now + timedelta(minutes=options["minutes"])
        silent = options["no_telegram"]

        # ✏️  Adjust field name to match your model
        upcoming = Booking.objects.filter(
            check_in__gte=now,
            check_in__lte=soon,
        ).order_by("check_in")

        # ── No bookings ──────────────────────────────────────────
        if not upcoming.exists():
            msg = f"✅ No bookings in the next {options['minutes']} minutes."
            self.stdout.write(self.style.WARNING(msg))
            if not silent:
                send_telegram_message(msg)
            return

        # ── Summary header ───────────────────────────────────────
        count = upcoming.count()

        # ── Per-booking messages ─────────────────────────────────
        for booking in upcoming:
            minutes_away = int((booking.check_in - now).total_seconds() // 60)
            local_time   = timezone.localtime(booking.check_in).strftime("%Y-%m-%d %H:%M")

            # ✏️  Adjust fields to match your model
            customer = getattr(booking, "guest", "N/A")
            house = getattr(booking, "house")
            # Console output
            houseMap = {
                'family': "💙 Family House",
                'left': "💚 River View Left",
                'right': "🩶 River View Right"
            }

            # Telegram message (HTML formatted)
            telegram_text = (
                f"<b>{customer}</b> {houseMap[house]} \n"
                f"через {minutes_away} хв"
            )

            if not silent:
                ok = send_telegram_message(telegram_text)



