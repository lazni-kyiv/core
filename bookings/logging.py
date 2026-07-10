from django.forms.models import model_to_dict
from typing import TYPE_CHECKING

from .models import Booking, BookingLog, BOOKING_UNTRACKED_FIELDS

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser


# -----------------------------
# helpers
# -----------------------------

from django.forms.models import model_to_dict
from .utils import json_safe


def _snapshot(booking):
    data = model_to_dict(booking)
    data["id"] = str(booking.pk)

    return json_safe(data)


def _diff(old, new):
    result = {}
    keys = set(old) | set(new)

    for key in keys:
        if key in BOOKING_UNTRACKED_FIELDS:
            continue

        old_val = old.get(key)
        new_val = new.get(key)

        if old_val != new_val:
            result[key] = {
                "old": json_safe(old_val),
                "new": json_safe(new_val),
            }

    return result


def _actor_label(actor: "AbstractBaseUser | None") -> str:
    if not actor:
        return "system"
    return actor.get_username() or str(actor.pk)


# -----------------------------
# public API
# -----------------------------

def log_create(booking: Booking, actor=None, remote_addr=None):
    snap = _snapshot(booking)

    return BookingLog.objects.create(
        booking=booking,
        booking_id_snapshot=str(booking.pk),
        booking_label_snapshot=str(booking),
        action=BookingLog.Action.CREATE,
        actor=actor,
        actor_label=_actor_label(actor),
        diff={},
        snapshot=snap,
        remote_addr=remote_addr,
    )


def log_update(booking: Booking, old_snapshot: dict, actor=None, remote_addr=None):
    new_snapshot = _snapshot(booking)
    diff = _diff(old_snapshot, new_snapshot)

    if not diff:
        return None

    return BookingLog.objects.create(
        booking=booking,
        booking_id_snapshot=str(booking.pk),
        booking_label_snapshot=str(booking),
        action=BookingLog.Action.UPDATE,
        actor=actor,
        actor_label=_actor_label(actor),
        diff=diff,
        snapshot=new_snapshot,
        remote_addr=remote_addr,
    )


def log_delete(booking: Booking, old_snapshot: dict, actor=None, remote_addr=None):
    return BookingLog.objects.create(
        booking=None,
        booking_id_snapshot=str(old_snapshot.get("id", "")),
        booking_label_snapshot=str(old_snapshot),
        action=BookingLog.Action.DELETE,
        actor=actor,
        actor_label=_actor_label(actor),
        diff={},
        snapshot=old_snapshot,
        remote_addr=remote_addr,
    )