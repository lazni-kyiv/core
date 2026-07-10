from rest_framework import serializers
from django.contrib.auth import authenticate


class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(
            request=self.context.get('request'),
            username=data['email'],
            password=data['password'],
        )
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled")
        data['user'] = user
        return data


class UserSerializer(serializers.Serializer):
    id = serializers.CharField()
    email     = serializers.EmailField()
    full_name = serializers.SerializerMethodField()
    groups    = serializers.SerializerMethodField()
    is_staff  = serializers.BooleanField()
    permissions = serializers.SerializerMethodField()
    password_changed_at = serializers.DateTimeField(
        source='profile.password_changed_at', read_only=True
    )
    pin_changed_at = serializers.DateTimeField(
        source='profile.pin_changed_at', read_only=True
    )
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_groups(self, obj):
        return list(obj.groups.values_list('name', flat=True))

    def get_permissions(self, obj):
        # Всі permissions юзера включаючи групові
        return list(obj.get_all_permissions())

    class Meta:

        fields = ['password_changed_at', 'pin_changed_at']