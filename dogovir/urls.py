from django.urls import path

from .views import ContractsView, DogovirTextView

urlpatterns = [
    path(
        "",
        ContractsView.as_view(),
        name="contracts",
    ),
    path(
        "template/",
        DogovirTextView.as_view(),
        name="template",
    ),
]