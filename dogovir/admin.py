from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import display, action
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm, SelectableFieldsExportForm

from .models import DogovirText, TextStyle

STYLE_COLORS = {
    TextStyle.LEFT_BOLD: "danger",
    TextStyle.LEFT_SEMI_BOLD: "warning",
    TextStyle.LEFT_NORMAL: "info",
}


class DogovirTextResource(resources.ModelResource):
    class Meta:
        model = DogovirText


@admin.register(DogovirText)
class DogovirTextAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = DogovirTextResource
    import_form_class = ImportForm
    export_form_class = SelectableFieldsExportForm
    import_export_change_list_template = "admin/change_list.html"

    list_display = ("order", "display_style", "short_title")
    list_display_links = ("order", "short_title")
    list_editable = ()
    search_fields = ("title",)
    list_filter = ("style",)
    list_filter_submit = True
    list_fullwidth = True
    compressed_fields = True
    warn_unsaved_form = True
    ordering = ("order",)
    actions_list = ["action_import", "action_export"]

    @action(description="Import")
    def action_import(self, request):
        from django.shortcuts import redirect
        return redirect("../import/")

    @action(description="Export")
    def action_export(self, request):
        from django.shortcuts import redirect
        return redirect("../export/")

    @display(
        description=_("Style"),
        ordering="style",
        label={s: STYLE_COLORS[s] for s in TextStyle},
    )
    def display_style(self, obj):
        return obj.style

    @display(description=_("Title"))
    def short_title(self, obj):
        return obj.title[:80] + ("…" if len(obj.title) > 80 else "")