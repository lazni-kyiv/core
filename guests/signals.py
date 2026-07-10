from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from .models import Guest


@receiver(post_save, sender=Guest)
def clear_guest_cache(sender, instance, **kwargs):
    cache.clear()


@receiver(post_delete, sender=Guest)
def clear_guest_cache_delete(sender, instance, **kwargs):
    cache.clear()