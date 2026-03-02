import os
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from .models import EmployeeDocument, CompanyPolicy, Employee, PolicyAcknowledgement

# Helper function
def delete_file(instance):
    if instance.file and os.path.isfile(instance.file.path):
        os.remove(instance.file.path)

# Delete files when EmployeeDocument is removed
@receiver(post_delete, sender=EmployeeDocument)
def auto_delete_employee_document_file(sender, instance, **kwargs):
    delete_file(instance)

# Delete files when CompanyPolicy is removed
@receiver(post_delete, sender=CompanyPolicy)
def auto_delete_company_policy_file(sender, instance, **kwargs):
    delete_file(instance)

# Assign policies when a new Employee is created
@receiver(post_save, sender=Employee)
def assign_standard_policies(sender, instance, created, **kwargs):
    if created:
        active_policies = CompanyPolicy.objects.filter(
            tenant=instance.tenant,
            is_active=True
        )
        for policy in active_policies:
            PolicyAcknowledgement.objects.create(
                tenant=instance.tenant,
                employee=instance,
                policy=policy
            )