from django.core.management.base import BaseCommand
from org.models import Tenant
from customer.models import (
    CRMUser, Account, Contact, Lead, Opportunity, Customer, Transaction,
    LoanReport, BranchPerformance, Prompt, LLM, Tenant_AI, Conversation
)
from django.db import transaction

class Command(BaseCommand):
    help = 'Maps all existing records in the customer app models to the tenant with code "DMC"'

    def handle(self, *args, **kwargs):
        try:
            tenant = Tenant.objects.get(code="DMC")
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR('Tenant with code "DMC" does not exist.'))
            return

        models_to_update = [
            CRMUser, Account, Contact, Lead, Opportunity, Customer, Transaction,
            LoanReport, BranchPerformance
        ]

        total_updated = 0

        with transaction.atomic():
            for model in models_to_update:
                try:
                    # Use all_objects if available to bypass tenant filtering in the manager
                    manager = getattr(model, 'all_objects', model.objects)
                    
                    # Update all records for the model to belong to the "DMC" tenant
                    updated_count = manager.all().update(tenant=tenant)
                    total_updated += updated_count
                    
                    self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} records for {model.__name__}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Failed to update {model.__name__}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Finished mapping {total_updated} total records to the "DMC" tenant.'))
