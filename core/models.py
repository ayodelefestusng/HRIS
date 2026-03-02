from django.db import models

from org.models import TenantModel,tenant_directory_path
from django.contrib.auth import get_user_model

User = get_user_model()
# Create your models here.
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50) # Basic, Professional, Enterprise
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    per_employee_cost = models.DecimalField(max_digits=10, decimal_places=2)
    max_employees = models.PositiveIntegerField(default=50)
    features = models.JSONField(default=dict) # {"has_payroll": True, "has_ats": False}

    def __str__(self):
        return self.name

class Invoice(TenantModel):
    billing_period = models.DateField()
    employee_count = models.PositiveIntegerField()
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    invoice_pdf = models.FileField(upload_to=tenant_directory_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Inv {self.billing_period.strftime('%b %Y')} - {self.tenant.name}"


    
class GlobalAuditLog(models.Model):
    # Not a TenantModel, because it's for the Super Admin to see ALL tenants
    tenant = models.ForeignKey('org.Tenant', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255) # e.g., "USER_DEACTIVATED"
    module = models.CharField(max_length=50) # e.g., "PAYROLL"
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']