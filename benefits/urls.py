from rest_framework.routers import DefaultRouter
from .views import GradeHealthInsuranceViewSet, ReimbursementViewSet

router = DefaultRouter()
router.register(r"health-insurance", GradeHealthInsuranceViewSet)
router.register(r"reimbursements", ReimbursementViewSet)

urlpatterns = router.urls

from django.urls import path
from . import views

urlpatterns = [
    # path('subscription/', views.billing_dashboard, name='billing_dashboard'),
    # path('invoice/<int:pk>/pay/', views.process_payment, name='process_payment'),
]