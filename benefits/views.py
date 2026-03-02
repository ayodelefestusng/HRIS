from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import GradeHealthInsurance, Reimbursement
from .serializers import GradeHealthInsuranceSerializer, ReimbursementSerializer
import logging
from rest_framework import viewsets

logger = logging.getLogger(__name__)

def log_with_context(level, message, user):
    tenant = getattr(user, "tenant", None)
    logger.log(
        level,
        f"tenant={tenant}|user={user.username}|{message}"
    )

class GradeHealthInsuranceViewSet(viewsets.ModelViewSet):
    queryset = GradeHealthInsurance.objects.all()
    serializer_class = GradeHealthInsuranceSerializer

    def get_queryset(self):
        # Ensure tenant isolation in the API
        return self.queryset.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        log_with_context(logging.INFO, "Creating GradeHealthInsurance record", self.request.user)
        serializer.save(tenant=self.request.user.tenant)

    def perform_update(self, serializer):
        log_with_context(logging.INFO, f"Updating GradeHealthInsurance ID: {self.get_object().pk}", self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        log_with_context(logging.WARNING, f"Deleting GradeHealthInsurance ID: {instance.pk}", self.request.user)
        instance.delete()


class ReimbursementViewSet(viewsets.ModelViewSet):
    queryset = Reimbursement.objects.all()
    serializer_class = ReimbursementSerializer

    def get_queryset(self):
        # Ensure tenant isolation in the API
        return self.queryset.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        log_with_context(logging.INFO, "Submitting new Reimbursement request", self.request.user)
        serializer.save(tenant=self.request.user.tenant)

    def perform_update(self, serializer):
        # Useful for tracking status changes (Approved/Rejected)
        instance = self.get_object()
        log_with_context(logging.INFO, f"Updating Reimbursement ID: {instance.pk}", self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        log_with_context(logging.WARNING, f"Deleting Reimbursement ID: {instance.pk}", self.request.user)
        instance.delete()