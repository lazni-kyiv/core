from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from django_json_widget.widgets import JSONEditorWidget
from . import logging as booking_logging
from .logging import _snapshot
from .models import Booking, BookingLog
from django.db import models
from django.utils.html import format_html, escape
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm, SelectableFieldsExportForm
from django.utils.safestring import mark_safe


# --------------------------------------------------
# RESOURCE
# --------------------------------------------------

class BookingResource(resources.ModelResource):
    class Meta:
        model = Booking
        fields = ('id', 'house', 'type', 'guest', 'check_in', 'check_out', 'totalcost', 'prepayment', 'source', 'comment', 'created_at', 'updated_at')


# --------------------------------------------------
# LOG INLINE
# --------------------------------------------------

class BookingLogInline(TabularInline):
    model = BookingLog
    extra = 0
    can_delete = False
    max_num = 0
    show_change_link = False
    fk_name = "booking"

    fields = ("timestamp", "actor_label", "action_badge", "diff_display")
    readonly_fields = ("timestamp", "actor_label", "action_badge", "diff_display")
    ordering = ("-timestamp",)

    verbose_name = _("Log entry")
    verbose_name_plural = _("History")

    def action_badge(self, obj):
        colors = {
            BookingLog.Action.CREATE: ("#E1F5EE", "#085041"),
            BookingLog.Action.UPDATE: ("#FAEEDA", "#633806"),
            BookingLog.Action.DELETE: ("#FCEBEB", "#791F1F"),
        }
        bg, fg = colors.get(obj.action, ("#F1EFE8", "#444441"))

        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;'
            'border-radius:999px;font-size:12px;font-weight:500">{}</span>',
            bg, fg, obj.get_action_display(),
        )

    action_badge.short_description = _("Action")

    def diff_display(self, obj):
        if not obj.diff:
            return "—"

        lines = []
        for field, change in obj.diff.items():
            old = escape(str(change.get("old") or "—"))
            new = escape(str(change.get("new") or "—"))

            lines.append(
                f'<span style="font-size:12px;color:#888">{escape(field)}:</span> '
                f'<span style="text-decoration:line-through;color:#E24B4A">{old}</span>'
                f' → <span style="color:#1D9E75">{new}</span>'
            )

        return mark_safe("<br>".join(lines))

    diff_display.short_description = _("Changes")


# --------------------------------------------------
# BOOKING ADMIN
# --------------------------------------------------

from unfold.decorators import action

@admin.register(Booking)
class BookingAdmin(ImportExportModelAdmin, ModelAdmin):
    ...
    actions_list = ["action_import", "action_export"]

    @action(description="Import")
    def action_import(self, request):
        from django.shortcuts import redirect
        return redirect("../import/")

    @action(description="Export")
    def action_export(self, request):
        from django.shortcuts import redirect
        return redirect("../export/")
    resource_class = BookingResource
    import_form_class = ImportForm
    export_form_class = SelectableFieldsExportForm
    import_export_change_list_template = "admin/change_list.html"

    formfield_overrides = {
        models.JSONField: {
            "widget": JSONEditorWidget(options={
                "mode": "tree",
            })
        },
    }
    list_display = (
        "id",
        "house",
        "type",
        "guest",
        "check_in",
        "check_out",
        "totalcost",
        "prepayment",
        "created_at",
    )

    search_fields = ("guest__name", "comment")
    list_filter = ("house", "type", "source")
    ordering = ("-check_in",)

    readonly_fields = ("id", "created_at", "updated_at")

    inlines = [BookingLogInline]

    fieldsets = (
        (_("Основне"), {
            "fields": (
                "id",
                "guest",
                "house",
                "type",
                "source"
            ),
            "classes": ("tab",),
        }),

        (_("Дати"), {
            "fields": (
                "check_in",
                "check_out",
                "extensions"
            ),
            "classes": ("tab",),
        }),

        (_("Фінанси"), {
            "fields": (
                "totalcost",
                "prepayment",
            ),
            "classes": ("tab",),
        }),

        (_("Дані"), {
            "fields": (
                "guests",
                "extra",
                "lazni",
                "dogovir",
                "comment",
            ),
            "classes": ("tab",),
        }),

        (_("Система"), {
            "fields": (
                "created_at",
                "updated_at",
                "gcal_event_id"
            ),
            "classes": ("tab",),
        }),
    )

    def save_model(self, request, obj, form, change):
        if change:
            old_snapshot = _snapshot(Booking.objects.get(pk=obj.pk))

        super().save_model(request, obj, form, change)

        if change:
            booking_logging.log_update(
                obj,
                old_snapshot,
                actor=request.user,
            )
        else:
            booking_logging.log_create(
                obj,
                actor=request.user,
            )

    def delete_model(self, request, obj):
        old_snapshot = _snapshot(obj)

        super().delete_model(request, obj)

        booking_logging.log_delete(
            obj,
            old_snapshot,
            actor=request.user,
        )


# --------------------------------------------------
# LOG ADMIN
# --------------------------------------------------

@admin.register(BookingLog)
class BookingLogAdmin(ModelAdmin):
    list_display = (
        "timestamp",
        "booking_label_snapshot",
        "action",
        "actor_label",
        "remote_addr",
    )

    search_fields = (
        "booking_label_snapshot",
        "booking_id_snapshot",
        "actor_label",
    )

    readonly_fields = (
        "timestamp",
        "booking",
        "booking_id_snapshot",
        "booking_label_snapshot",
        "action",
        "actor",
        "actor_label",
        "diff",
        "snapshot",
        "remote_addr",
    )

    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False