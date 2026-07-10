from rest_framework import serializers
from .models import Booking
from .utils import json_safe


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = "__all__"

    def validate(self, data):
        data["lazni"] = json_safe(data.get("lazni", {}))
        data["dogovir"] = json_safe(data.get("dogovir", {}))
        data["extra"] = json_safe(data.get("extra", {}))
        return data

    # Source - https://stackoverflow.com/a/35884710
    # Posted by Andriy Ivaneyko, modified by community. See post 'Timeline' for change history
    # Retrieved 2026-06-25, License - CC BY-SA 4.0

   
