from django.db import models

class GlobalPermissions(models.Model):
    class Meta:
        managed = False 
        default_permissions = ()
        permissions = [
            ("view_analytics", "Can view analytics"),
            ("view_reports", "Can view reports"),
            ("view_export", "Can export"),
            ("view_contract", "Can view contract"),
            ("show_contract", "Can show contract to guests"),
            ("requires_pwa", "Requires PWA"),
            ("view_personal_data", "View guests personal data"),
        ]

from django.db import models

class SystemConfig(models.Model):
    site_stats_api_key = models.CharField(max_length=255)
    bot_stats_api_key = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise Exception("Deletion is not allowed")

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "System Configuration"


from django.db import models

from django.conf import settings

class RequestLog(models.Model):
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    status_code = models.IntegerField()
    response_time_ms = models.IntegerField()
    ip_address = models.GenericIPAddressField(null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']