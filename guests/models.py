from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()

import uuid
def generate_short_uuid():
    return uuid.uuid4().hex[:12]

class Guest(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=12,
        default=generate_short_uuid,
        editable=False,
    )

    alias = models.CharField(_("Alias"), max_length=50)
    source = models.CharField(_("Source"), max_length=30)
    instagram = models.CharField(_("Instagram"), max_length=100, blank=True, null=True)
    telegram = models.CharField(_("Telegram"), max_length=100, blank=True,  null=True)

    comment = models.CharField(_("Comment"), max_length=255, blank=True, null=True)

    name = models.CharField(_("Full name"), max_length=255, blank=True, null=True)
    birthday = models.CharField(_("Birthday"), max_length=20, blank=True, null=True)
    phone = models.CharField(_("Phone"), max_length=30, blank=True, null=True)
    document = models.CharField(_("Document"), max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Guest")
        verbose_name_plural = _("Guests")
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or self.alias or self.id

GUEST_UNTRACKED_FIELDS = frozenset({"updated_at"})

class GuestLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", _("Created")
        UPDATE = "update", _("Updated")
        DELETE = "delete", _("Deleted")

    guest = models.ForeignKey(
        Guest,
        on_delete=models.SET_NULL,
        null=True,
        related_name="logs",
        verbose_name=_("Guest"),
        # Keep the log even after the guest is deleted
        db_constraint=True,
    )
    # Snapshot the guest id/name so the log is readable after deletion
    guest_id_snapshot = models.CharField(max_length=12, db_index=True)
    guest_name_snapshot = models.CharField(max_length=255, blank=True)

    action = models.CharField(_("Action"), max_length=10, choices=Action.choices)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guest_logs",
        verbose_name=_("Actor"),
    )
    actor_label = models.CharField(
        _("Actor label"),
        max_length=150,
        blank=True,
        help_text=_("Username snapshot at the time of the action"),
    )

    # JSON diff: {"field": {"old": ..., "new": ...}, ...}
    # Empty dict for CREATE / DELETE (full snapshot stored separately)
    diff = models.JSONField(_("Diff"), default=dict)

    # Full object snapshot for CREATE and DELETE for forensics
    snapshot = models.JSONField(_("Snapshot"), default=dict)

    timestamp = models.DateTimeField(_("Timestamp"), auto_now_add=True, db_index=True)
    remote_addr = models.GenericIPAddressField(_("IP address"), null=True, blank=True)

    class Meta:
        verbose_name = _("Guest log")
        verbose_name_plural = _("Guest logs")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["guest_id_snapshot", "-timestamp"]),
            models.Index(fields=["actor", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.action} · {self.guest_name_snapshot} · {self.timestamp:%Y-%m-%d %H:%M}"