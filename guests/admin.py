from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter
from unfold.decorators import action
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm, SelectableFieldsExportForm

from . import logging as guest_logging
from .logging import _snapshot
from .models import Guest, GuestLog


class GuestLogInline(TabularInline):
    model = GuestLog
    extra = 0
    can_delete = False
    max_num = 0
    show_change_link = False
    fk_name = "guest"

    fields = ("timestamp", "actor_label", "action_badge", "diff_display")
    readonly_fields = ("timestamp", "actor_label", "action_badge", "diff_display")
    ordering = ("-timestamp",)
    verbose_name = _("Log entry")
    verbose_name_plural = _("History")

    def action_badge(self, obj):
        colors = {
            GuestLog.Action.CREATE: ("#E1F5EE", "#085041"),
            GuestLog.Action.UPDATE: ("#FAEEDA", "#633806"),
            GuestLog.Action.DELETE: ("#FCEBEB", "#791F1F"),
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
            old = change.get("old") or "—"
            new = change.get("new") or "—"
            lines.append(
                f'<span style="font-size:12px;color:#888">{field}:</span> '
                f'<span style="text-decoration:line-through;color:#E24B4A">{old}</span>'
                f' → <span style="color:#1D9E75">{new}</span>'
            )
        return format_html("<br>".join(lines))
    diff_display.short_description = _("Changes")


class GuestResource(resources.ModelResource):
    class Meta:
        model = Guest
        fields = ('id', 'name', 'alias', 'phone', 'source', 'instagram', 'telegram', 'birthday', 'document', 'comment', 'created_at', 'updated_at')


@admin.register(Guest)
class GuestAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = GuestResource
    import_form_class = ImportForm
    export_form_class = SelectableFieldsExportForm
    import_export_change_list_template = "admin/change_list.html"

    list_display = ("name", "alias", "phone", "source", "instagram", "telegram", "created_at")
    search_fields = ("name", "alias", "phone", "instagram", "telegram")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    inlines = [GuestLogInline]
    actions_list = ["action_import", "action_export"]

    fieldsets = (
        (_("Інфо"), {"fields": ("id", "alias", "source", "comment"), "classes": ("tab",)}),
        (_("Особиста інформація"), {"fields": ("name", "phone", "birthday", "document"), "classes": ("tab",)}),
        (_("Мета"), {"fields": ("created_at", "updated_at", "instagram", "telegram"), "classes": ("tab",)}),
    )

    @action(description="Import")
    def action_import(self, request):
        from django.shortcuts import redirect
        return redirect("../import/")

    @action(description="Export")
    def action_export(self, request):
        from django.shortcuts import redirect
        return redirect("../export/")

    def save_model(self, request, obj, form, change):
        if change:
            old_snapshot = _snapshot(Guest.objects.get(pk=obj.pk))
        super().save_model(request, obj, form, change)
        if change:
            guest_logging.log_update(obj, old_snapshot, actor=request.user)
        else:
            guest_logging.log_create(obj, actor=request.user)

    def delete_model(self, request, obj):
        old_snapshot = _snapshot(obj)
        super().delete_model(request, obj)
        guest_logging.log_delete(obj, old_snapshot, actor=request.user)


@admin.register(GuestLog)
class GuestLogAdmin(ModelAdmin):
    list_display = ("timestamp", "guest_name_snapshot", "action", "actor_label", "remote_addr")
    # list_filter = (
    #     ("action", ChoicesDropdownFilter),
    # )
    search_fields = ("guest_name_snapshot", "guest_id_snapshot", "actor_label")
    readonly_fields = fields = (
        "timestamp", "guest", "guest_id_snapshot", "guest_name_snapshot",
        "action", "actor", "actor_label", "diff", "snapshot", "remote_addr",
    )
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False