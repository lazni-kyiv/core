# access/models.py
import uuid
import secrets
import string
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password as django_check_password

from user_agents import parse


def get_device_info(request):
    ua_string = request.META.get("HTTP_USER_AGENT", "")
    ua = parse(ua_string)

    device_name = (
        ua.device.family
        if ua.device.family != "Other"
        else f"{ua.os.family} {ua.browser.family}"
    )

    print(ua)

    return {
        "user_agent": ua_string,
        "device_name": device_name,
        "browser": f"{ua.browser.family} {ua.browser.version_string}",
        "os": f"{ua.os.family} {ua.os.version_string}",
    }
    
def generate_id():
    full_uuid = uuid.uuid4().hex
    return full_uuid[:20]


class User(AbstractUser):
    id = models.CharField(
        primary_key=True,
        max_length=20,
        default=generate_id,
        editable=False,
        unique=True
    )

    class Meta:
        db_table = 'auth_user'
        app_label = 'access'
        swappable = 'AUTH_USER_MODEL'
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.email or self.username


class UserProfile(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=20,
        default=generate_id,
        editable=False,
        unique=True
    )
    user = models.OneToOneField(
        'access.User',
        on_delete=models.CASCADE,
        related_name='profile'
    )
    pin_hash = models.CharField(max_length=128, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    password_changed_at = models.DateTimeField(null=True, blank=True)
    pin_changed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'access'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def set_pin(self, raw_pin):
        """
        Hash and set the PIN for the user
        """
        if raw_pin:
            self.pin_hash = make_password(str(raw_pin))
            self.save(update_fields=['pin_hash', 'updated_at'])
        else:
            self.pin_hash = ''
            self.save(update_fields=['pin_hash', 'updated_at'])

    def check_pin(self, raw_pin):
        """
        Verify the PIN against the stored hash
        """
        if not self.pin_hash:
            return False
        return django_check_password(str(raw_pin), self.pin_hash)

    def has_pin(self):
        """
        Check if user has a PIN set
        """
        return bool(self.pin_hash)

    def __str__(self):
        return f"{self.user.email} - Profile"


class ActiveToken(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=20,
        default=generate_id,
        editable=False,
        unique=True
    )
    user = models.ForeignKey(
        'access.User',
        on_delete=models.CASCADE,
        related_name='active_tokens'
    )
    jti = models.CharField(max_length=255, unique=True)
    token_type = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)

    # user_agent = models.TextField(blank=True)
    # ip_address = models.GenericIPAddressField(null=True, blank=True)

    # device_name = models.CharField(max_length=255, blank=True)
    # browser = models.CharField(max_length=100, blank=True)
    # os = models.CharField(max_length=100, blank=True)


    class Meta:
        ordering = ['-created_at']
        app_label = 'access'

    def is_valid(self):
        return not self.revoked and timezone.now() < self.expires_at

    @classmethod
    def revoke_all(cls, user):
        cls.objects.filter(user=user, revoked=False).update(revoked=True)

    @classmethod
    def cleanup_expired(cls):
        deleted_count, _ = cls.objects.filter(expires_at__lt=timezone.now()).delete()
        return deleted_count

    def __str__(self):
        return f"{self.user.email} - {self.token_type}"


class LoginLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        FAILED = 'failed', 'Failed attempt'

    id = models.CharField(
        primary_key=True,
        max_length=20,
        default=generate_id,
        editable=False,
        unique=True
    )
    user = models.ForeignKey(
        'access.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    email = models.EmailField()
    action = models.CharField(max_length=10, choices=Action.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        app_label = 'access'

    def __str__(self):
        return f"{self.email} — {self.action} — {self.created_at:%Y-%m-%d %H:%M}"