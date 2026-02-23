from rest_framework.routers import DefaultRouter
from .views import VerificationSessionViewSet

router = DefaultRouter()
router.register("verification-sessions", VerificationSessionViewSet, basename="verificationsession")

urlpatterns = router.urls
