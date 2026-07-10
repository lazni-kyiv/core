from __future__ import annotations

from typing import TYPE_CHECKING

from django.forms.models import model_to_dict

from .models import GUEST_UNTRACKED_FIELDS, Guest, GuestLog

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _snapshot(guest: Guest) -> dict:
    data = model_to_dict(guest)
    data["id"] = guest.pk
    # Ensure datetimes are strings
    for field in ("created_at", "updated_at"):
        value = getattr(guest, field, None)
        if value is not None:
            data[field] = value.isoformat()
    return data


def _diff(old: dict, new: dict) -> dict:
    result = {}
    all_keys = set(old) | set(new)
    for key in all_keys:
        if key in GUEST_UNTRACKED_FIELDS:
            continue
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            result[key] = {"old": old_val, "new": new_val}
    return result


def _actor_label(actor: AbstractBaseUser | None) -> str:
    if actor is None:
        return "system"
    return actor.get_username() or str(actor.pk)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_create(
    guest: Guest,
    actor=None,
    remote_addr: str | None = None,
) -> GuestLog:
    snap = _snapshot(guest)
    return GuestLog.objects.create(
        guest=guest,
        guest_id_snapshot=guest.pk,
        guest_name_snapshot=str(guest),
        action=GuestLog.Action.CREATE,
        actor=actor,
        actor_label=_actor_label(actor),
        diff={},           # nothing to diff on create
        snapshot=snap,
        remote_addr=remote_addr,
    )


def log_update(
    guest: Guest,
    old_snapshot: dict,
    actor=None,
    remote_addr: str | None = None,
) -> GuestLog | None:
    new_snapshot = _snapshot(guest)
    diff = _diff(old_snapshot, new_snapshot)
    if not diff:
        return None   # nothing actually changed — skip the log entry
    return GuestLog.objects.create(
        guest=guest,
        guest_id_snapshot=guest.pk,
        guest_name_snapshot=str(guest),
        action=GuestLog.Action.UPDATE,
        actor=actor,
        actor_label=_actor_label(actor),
        diff=diff,
        snapshot=new_snapshot,
        remote_addr=remote_addr,
    )


def log_delete(
    guest: Guest,
    old_snapshot: dict,
    actor=None,
    remote_addr: str | None = None,
) -> GuestLog:
    return GuestLog.objects.create(
        guest=None,                       # FK will be NULL after deletion
        guest_id_snapshot=old_snapshot.get("id", ""),
        guest_name_snapshot=old_snapshot.get("name", ""),
        action=GuestLog.Action.DELETE,
        actor=actor,
        actor_label=_actor_label(actor),
        diff={},
        snapshot=old_snapshot,
        remote_addr=remote_addr,
    )