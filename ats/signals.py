import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from ats.models import Application
from .models import OnboardingPlan, OnboardingTask, OnboardingTemplate
from employees.models import Employee
from django.db import transaction
from ats.models import OnboardingRequirement


logger = logging.getLogger(__name__)


@receiver(post_save, sender=Application)
def trigger_onboarding_on_hire(sender, instance, created, **kwargs):
    """
    1. Updates Candidate to 'HIRED'.
    2. Creates the Employee profile.
    3. Initializes the OnboardingPlan and links specific Requirements.
    """
    if instance.status == "HIRED" and not hasattr(instance, 'onboarding_plan'):
        try:
            with transaction.atomic():
                # A. Create the Employee Profile First
                # This gives the newcomer access to the "Employee Cockpit"
                new_employee = Employee.objects.create(
                    tenant=instance.tenant,
                    user=instance.candidate.user, # Assuming Candidate links to User
                    first_name=instance.candidate.first_name,
                    last_name=instance.candidate.last_name,
                    email=instance.candidate.email,
                    status="ONBOARDING", # Keep them in onboarding state
                    date_joined=timezone.now().date()
                )

                # B. Create the Onboarding Plan
                plan = OnboardingPlan.objects.create(
                    application=instance,
                    employee=new_employee, # Linked to the new profile
                    tenant=instance.tenant,
                    start_date=timezone.now().date() + timedelta(days=7),
                    status="IN_PROGRESS"
                )

                # C. Fetch Template & Requirements
                default_template = OnboardingTemplate.objects.filter(
                    tenant=instance.tenant, 
                    name__icontains="Default"
                ).prefetch_related('task_templates').first()

                if default_template:
                    for tmpl in default_template.task_templates.all():
                        # Link task to a Requirement if it exists
                        # This allows the UI to know it's a 'DOCUMENT' or 'ACKNOWLEDGEMENT'
                        requirement, _ = OnboardingRequirement.objects.get_or_create(
                            tenant=instance.tenant,
                            name=tmpl.title,
                            defaults={'req_type': 'DOCUMENT'} # Defaulting for safety
                        )

                        OnboardingTask.objects.create(
                            plan=plan,
                            employee=new_employee,
                            tenant=instance.tenant,
                            requirement=requirement, # Harmonized link
                            title=tmpl.title,
                            description=tmpl.description,
                            due_date=plan.start_date + timedelta(days=tmpl.required_days)
                        )
                
                logger.info(f"Onboarding initialized for {new_employee.first_name}")

        except Exception as e:
            logger.error(f"Critical error in onboarding signal for App {instance.id}: {str(e)}")