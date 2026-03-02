from rest_framework.routers import DefaultRouter
from .views import WarningViewSet, SuspensionViewSet, InvestigationViewSet

router = DefaultRouter()
router.register(r"warnings", WarningViewSet)
router.register(r"suspensions", SuspensionViewSet)
router.register(r"investigations", InvestigationViewSet)

urlpatterns = router.urls