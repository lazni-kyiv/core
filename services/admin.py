from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display, action
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm, SelectableFieldsExportForm

from .models import AuthorSpecial, Complex, KramItem, KramSection, Service, ServiceType


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

class AuthorSpecialResource(resources.ModelResource):
    class Meta:
        model = AuthorSpecial

class ComplexResource(resources.ModelResource):
    class Meta:
        model = Complex

class ServiceResource(resources.ModelResource):
    class Meta:
        model = Service

class KramItemResource(resources.ModelResource):
    class Meta:
        model = KramItem


# ---------------------------------------------------------------------------
# Author Specials
# ---------------------------------------------------------------------------

@admin.register(AuthorSpecial)
class AuthorSpecialAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = AuthorSpecialResource
    import_form_class = ImportForm
    export_form_class = SelectableFieldsExportForm
    import_export_change_list_template = "admin/change_list.html"
    actions_list = ["action_import", "action_export"]

    list_display = ("name", "id")
    search_fields = ("name",)
    list_fullwidth = True
    compressed_fields = True
    warn_unsaved_form = True

    @action(description="Import")
    def action_import(self, request):
        from django.shortcuts import redirect
        return redirect("../import/")

    @action(description="Export")
    def action_export(self, request):
        from django.shortcuts import redirect
        return redirect("../export/")


# ---------------------------------------------------------------------------
# Complexes
# ---------------------------------------------------------------------------

@admin.register(Complex)
class ComplexAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = ComplexResource
    import_form_class = ImportForm
    export_form_class = SelectableFieldsExportForm
    import_export_change_list_template = "admin/change_list.html"
    actions_list = ["action_import", "action_export"]

    list_display = ("name", "id")
    search_fields = ("name",)
    list_fullwidth = True
    compressed_fields = True
    warn_unsaved_form = True

    @action(description="Import")
    def action_import(self, request):
        from django.shortcuts import redirect
        return redirect("../import/")

    @action(description="Export")
    def action_export(self, request):
        from django.shortcuts import redirect
        return redirect("../export/")


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

class ServiceTypeInline(TabularInline):
    model = ServiceType
    extra = 1
    fields = ("id", "name")
    tab = True


@admin.register(Service)
class ServiceAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = ServiceResource
    import_form_class = ImportForm
    export_form_class = SelectableFieldsExportForm
    import_export_change_list_template = "admin/change_list.html"
    actions_list = ["action_import", "action_export"]

    list_display = ("name", "display_has_types", "id")
    search_fields = ["name"]
    list_fullwidth = True
    compressed_fields = True
    warn_unsaved_form = True
    inlines = [ServiceTypeInline]

    @action(description="Import")
    def action_import(self, request):
        from django.shortcuts import redirect
        return redirect("../import/")

    @action(description="Export")
    def action_export(self, request):
        from django.shortcuts import redirect
        return redirect("../export/")

    @display(description=_("Has types"), label=True)
    def display_has_types(self, obj):
        has = obj.types.exists()
        return ("yes", "success") if has else ("no", "warning")


# ---------------------------------------------------------------------------
# Kram
# ---------------------------------------------------------------------------

SECTION_COLORS = {
    KramSection.ADDITIONAL: "info",
    KramSection.DRINKS: "success",
    KramSection.MASSAGERS: "warning",
    KramSection.SNACKS: "danger",
    KramSection.SOUVENIRS: "info",
}


@admin.register(KramItem)
class KramItemAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = KramItemResource
    import_form_class = ImportForm
    export_form_class = SelectableFieldsExportForm
    import_export_change_list_template = "admin/change_list.html"
    actions_list = ["action_import", "action_export"]

    list_display = ("name", "display_section", "id")
    list_filter = ["section"]
    search_fields = ["name"]
    list_fullwidth = True
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True

    @action(description="Import")
    def action_import(self, request):
        from django.shortcuts import redirect
        return redirect("../import/")

    @action(description="Export")
    def action_export(self, request):
        from django.shortcuts import redirect
        return redirect("../export/")

    @display(
        description=_("Section"),
        ordering="section",
        label={s: SECTION_COLORS[s] for s in KramSection},
    )
    def display_section(self, obj):
        return obj.section