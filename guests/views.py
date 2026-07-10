from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets, status
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response

from . import logging as guest_logging
from .models import Guest
from .serializers import GuestListSerializer, GuestDetailSerializer
from django.db.models import Count

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def _get_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _actor(request):
    user = request.user
    return user if (user and user.is_authenticated) else None


# --------------------------------------------------
# VIEWSET
# --------------------------------------------------
@method_decorator(cache_page(60 * 2), name="list")
# @method_decorator(cache_page(60), name="retrieve")
class GuestViewSet(viewsets.ModelViewSet):
    permission_classes = [DjangoModelPermissions]

    def get_queryset(self):
        if self.action == "retrieve":
            # detail — підтягуємо повні бронювання
            return Guest.objects.prefetch_related("bookings").all()
        # list — тільки лічильник, без prefetch
        return Guest.objects.annotate(
            bookings_count=Count("bookings")
        ).all()

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["source"]
    search_fields = ["name", "alias", "phone", "instagram", "telegram"]
    ordering_fields = ["name", "created_at"]
    ordering = ["-created_at"]

    # 🔥 dynamic serializer
    def get_serializer_class(self):
        if self.action == "retrieve":
            return GuestDetailSerializer
        return GuestListSerializer

    # --------------------------------------------------
    # PERMISSIONS
    # --------------------------------------------------

    def list(self, request, *args, **kwargs):
        print(request.user.has_perm("cloud.view_personal_data"))
        if request.user.has_perm("guests.view_guest"):
            return super().list(request, *args, **kwargs)
        return Response("403 Action Forbidden", status=status.HTTP_403_FORBIDDEN)

    def retrieve(self, request, *args, **kwargs):
        print(request.user.has_perm("cloud.view_personal_data"))
        if request.user.has_perm("guests.view_guest"):
            return super().retrieve(request, *args, **kwargs)
        return Response("403 Action Forbidden", status=status.HTTP_403_FORBIDDEN)

    # --------------------------------------------------
    # LOGGING
    # --------------------------------------------------

    def perform_create(self, serializer):
        cache.clear()
        guest = serializer.save()
        guest_logging.log_create(
            guest,
            actor=_actor(self.request),
            remote_addr=_get_ip(self.request),
        )

    def perform_update(self, serializer):
        cache.clear()
        from .logging import _snapshot

        old_snapshot = _snapshot(serializer.instance)
        guest = serializer.save()

        guest_logging.log_update(
            guest,
            old_snapshot=old_snapshot,
            actor=_actor(self.request),
            remote_addr=_get_ip(self.request),
        )