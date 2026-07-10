from rest_framework.routers import DefaultRouter

from .views import GuestViewSet

router = DefaultRouter()
router.register(r"", GuestViewSet, basename="guest")

urlpatterns = router.urls