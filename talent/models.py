from operator import imod
from django.db import models

# Create your models here.
from django.db import models
# from employees.models import Employee
# from org.models import RoleProfile
from django.utils import timezone
from django.conf import settings
from org.models import TenantModel


     

class AppraisalTTTTTT(TenantModel):
    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted by employee"),
        ("MANAGER_REVIEW", "Under manager review"),
        ("COMPLETED", "Completed"),
    )

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="talent_appraisals",
    )
    role = models.ForeignKey(
        "org.RoleOfficerInCharge",
        on_delete=models.CASCADE,
        related_name="talent_appraisals",
    )
    period_label = models.CharField(
        max_length=100,
        help_text="e.g. 2025 H1, 2025 Annual",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    manager_reviewed_at = models.DateTimeField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.employee} - {self.period_label} ({self.role})"
    
  