from datetime import timedelta

from django.utils import timezone
from django.core.cache import cache
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response

from .models import Booking
from .serializers import BookingSerializer
from .logging import log_create, log_update, _snapshot
from .gcal import sync_booking_to_calendar


def _get_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _actor(request):
    return request.user if request.user.is_authenticated else None


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related("guest").all()
    serializer_class = BookingSerializer
    permission_classes = [DjangoModelPermissions]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["house", "guest", "source"]
    search_fields = ["comment"]
    ordering_fields = ["check_in", "created_at", "totalcost"]
    ordering = ["-check_in"]

    # ---------------- CREATE ----------------
    def perform_create(self, serializer):
        cache.clear()

        booking = serializer.save()

        log_create(
            booking,
            actor=_actor(self.request),
            remote_addr=_get_ip(self.request),
        )

        sync_booking_to_calendar(
            booking,
            description=self.request.data.get("gcal_description", "")
        )

    # ---------------- UPDATE ----------------
    def perform_update(self, serializer):
        cache.clear()

        old = _snapshot(serializer.instance)

        booking = serializer.save()
    

        print("RAW DB:", booking.check_in)
        booking.refresh_from_db()
        print("AFTER REFRESH:", booking.check_in)
        print("TO RESPONSE:", BookingSerializer(booking).data)
        
        log_update(
            booking,
            old_snapshot=old,
            actor=_actor(self.request),
            remote_addr=_get_ip(self.request),
        )

        try:
            sync_booking_to_calendar(
                booking,
                description=self.request.data.get("gcal_description", "")
            )
        except:
            pass

    # ---------------- DELETE BLOCK ----------------
    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Deletion of bookings is not permitted."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    # ---------------- EXTEND ----------------
    @action(detail=True, methods=["put"], url_path="extend")
    def extend(self, request, pk=None):
        if not request.user.has_perm("bookings.change_booking"):
            return Response(
                {"detail": "You do not have permission to extend bookings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        booking = self.get_object()

        try:
            hours = float(request.data.get("hours", 0))
        except (TypeError, ValueError):
            return Response({"error": "Invalid hours value."}, status=400)

        if hours <= 0:
            return Response({"error": "Hours must be positive."}, status=400)

        old_checkout = booking.check_out
        new_checkout = old_checkout + timedelta(hours=hours)

        booking.check_out = new_checkout
        booking.extensions = (booking.extensions or []) + [{
            "extended_at": timezone.now().isoformat(),
            "added_hours": hours,
            "old_checkout": old_checkout.isoformat(),
            "new_checkout": new_checkout.isoformat(),
            "actor": request.user.username if request.user.is_authenticated else "system",
        }]

        booking.save(update_fields=["check_out", "extensions"])

        log_update(
            booking,
            old_snapshot={"check_out": old_checkout.isoformat()},
            actor=_actor(request),
            remote_addr=_get_ip(request),
        )

        cache.clear()

        return Response(BookingSerializer(booking).data)