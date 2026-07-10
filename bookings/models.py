from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()

import uuid
def generate_short_uuid():
    return uuid.uuid4().hex[:12]

def default_dogovir():
    return {
        "drive_url": None,
        "file_url": None,
        "signed_at": None,
        "signed": False,
    }


BOOKING_UNTRACKED_FIELDS = frozenset({"updated_at", "extensions"})

from django.db import models

class HouseChoices(models.TextChoices):
    FAMILY = "family", "Family"
    LEFT = "left", "Left"
    RIGHT = "right", "Right"

class TypeChoices(models.TextChoices):
    FAMILY = "house", "House"
    LEFT = "lazni", "Lazni"
    RIGHT = "pool", "Pool"

class SourceChoices(models.TextChoices):
    INSTAGRAM = "i", "Instagram"
    TELEGRAM = "tg", "Telegram"
    VIBER = "v", "Viber"
    WHATSAPP = "w", "WhatsApp"
    PHONE = "t", "Phone"
    BOT = "b", "Bot"

class Booking(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=12,
        default=generate_short_uuid,
        editable=False,
    )

    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    # ✅ ENUM instead of FK
    house = models.CharField(
        max_length=100,
        choices=HouseChoices.choices
    )

    source = models.CharField(max_length=100, choices=SourceChoices.choices, blank=True, null=True)
    type = models.CharField(max_length=100, choices=TypeChoices.choices)

    guest = models.ForeignKey(
        "guests.Guest",
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    gcal_event_id = models.CharField(max_length=255, blank=True, null=True)

    extensions = models.JSONField(default=list, blank=True)

    # ✅ JSON fields (as you said)
    lazni = models.JSONField(default=dict, blank=True)
    dogovir = models.JSONField(default=default_dogovir, blank=True)

    extra = models.JSONField(default=dict, blank=True, null=True)

    guests = models.PositiveIntegerField(default=1)

    prepayment = models.DecimalField(max_digits=10, decimal_places=2, null=True,  blank=True)

    totalcost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-check_in"]

    def __str__(self):
        return f"Booking #{self.id} - {self.house} - {self.check_in}"




class BookingLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", _("Created")
        UPDATE = "update", _("Updated")
        DELETE = "delete", _("Deleted")

    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        related_name="logs",
    )

    booking_id_snapshot = models.CharField(max_length=20, db_index=True)
    booking_label_snapshot = models.CharField(max_length=255, blank=True)

    action = models.CharField(max_length=10, choices=Action.choices)

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_logs",
    )

    actor_label = models.CharField(max_length=150, blank=True)

    diff = models.JSONField(default=dict)
    snapshot = models.JSONField(default=dict)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    remote_addr = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]

   

    def __str__(self):
        return f"{self.action} · {self.booking_label_snapshot} · {self.timestamp:%Y-%m-%d %H:%M}"