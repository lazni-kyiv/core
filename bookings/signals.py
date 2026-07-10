from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from .models import Booking


@receiver(post_save, sender=Booking)
def clear_booking_cache(sender, instance, **kwargs):
    cache.clear()


@receiver(post_delete, sender=Booking)
def clear_booking_cache_delete(sender, instance, **kwargs):
    cache.clear()