from rest_framework import serializers
from .models import Guest
from bookings.models import Booking
from django.utils import timezone
from rest_framework import serializers


replacements = {
                "name": "•••• •••• ••••",
                "document": "•••••••••",
                "phone": "+380 •• ••• ••••",
                "birthday": "••.••.••••",
                "telegram": "@•••••",
                "instagram": "@•••••",
            }

class BookingFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = "__all__"

    # def _normalize_datetime(self, dt):
    #     if not dt:
    #         return None

    #     # переводим в локальное время сервера (опционально)
    #     dt = timezone.localtime(dt)

    #     # убираем timezone полностью
    #     return dt.strftime("%Y-%m-%dT%H:%M:%S")

    # def get_check_in(self, obj):
    #     return self._normalize_datetime(obj.check_in)

    # def get_check_out(self, obj):
    #     return self._normalize_datetime(obj.check_out)


class GuestListSerializer(serializers.ModelSerializer):
    bookings_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Guest
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)

        request = self.context.get("request")

        if request and not request.user.has_perm("cloud.view_personal_data"):
            

            for field, masked in replacements.items():
                if field in data and data[field]:
                    data[field] = masked

        return data


class GuestDetailSerializer(serializers.ModelSerializer):
    bookings = BookingFullSerializer(many=True, read_only=True)

    class Meta:
        model = Guest
        fields = "__all__"
    def to_representation(self, instance):
        data = super().to_representation(instance)

        request = self.context.get("request")

        if request and not request.user.has_perm("cloud.view_personal_data"):
           
            for field, masked in replacements.items():
                if field in data and data[field]:
                    data[field] = masked

        return data