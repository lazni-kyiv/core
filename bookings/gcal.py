from datetime import timedelta
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

HOUSE_NAMES = {
    'left':   'River View Left',
    'right':  'River View Right',
    'family': 'Family House',
}

HOUSE_COLORS = {
    'left':   'basil',      # зелений
    'right':  'graphite',   # сірий
    'family': 'blueberry',  # синій
}

def _gcal_service():
    creds = service_account.Credentials.from_service_account_file(
        str(settings.GOOGLE_CREDENTIALS),  # same service account
        scopes=["https://www.googleapis.com/auth/calendar"],
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)
# Google Calendar використовує числові id для кольорів
def _color_id(name: str) -> str:
    color_map = {
        "tomato":    "11",
        "flamingo":  "4",
        "tangerine": "6",
        "banana":    "5",
        "sage":      "2",
        "basil":     "10",
        "peacock":   "7",
        "blueberry": "9",
        "lavender":  "1",
        "grape":     "3",
        "graphite":  "8",
    }
    return color_map.get(name, "8")

def sync_booking_to_calendar(booking, description="", color=''):
    """Create or update a Google Calendar event for a booking."""
    try:
        service     = _gcal_service()
        calendar_id = settings.GOOGLE_CALENDAR_ID

        house = HOUSE_NAMES.get(booking.house, booking.house)
        guest = getattr(booking.guest, "alias", str(booking.guest))

        event_body = {
            "summary":     f"{guest}",
        "description": description,
        "colorId":     _color_id(HOUSE_COLORS[booking.house]),
            "start": {
                "dateTime": booking.check_in.isoformat(),
                "timeZone": "Europe/Kyiv",
            },
            "end": {
                "dateTime": booking.check_out.isoformat(),
                "timeZone": "Europe/Kyiv",
            },
        }

        if booking.gcal_event_id:
            service.events().update(
                calendarId=calendar_id,
                eventId=booking.gcal_event_id,
                body=event_body,
            ).execute()
            logger.info("GCal event updated: %s", booking.gcal_event_id)
        else:
            created = service.events().insert(
                calendarId=calendar_id,
                body=event_body,
            ).execute()
            booking.gcal_event_id = created["id"]
            booking.save(update_fields=["gcal_event_id"])
            logger.info("GCal event created: %s", booking.gcal_event_id)

    except Exception as exc:
        logger.error("GCal sync failed for booking %s: %s", booking.pk, exc)