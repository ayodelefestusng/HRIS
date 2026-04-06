# customer/management/commands/assign_nin.py

import random
from django.core.management.base import BaseCommand
from customer.models import Customer

class Command(BaseCommand):
    help = "Assign unique 11-digit NINs to existing customers without one"

    def handle(self, *args, **options):
        updated_count = 0

        # Collect all existing NINs to avoid duplicates
        existing_nins = set(
            Customer.objects.exclude(nin__isnull=True).exclude(nin="").values_list("nin", flat=True)
        )

        for customer in Customer.objects.filter(nin__isnull=True) | Customer.objects.filter(nin=""):
            # Generate a unique 11-digit NIN
            nin = None
            while not nin or nin in existing_nins:
                nin = str(random.randint(10**10, 10**11 - 1))  # 11-digit number

            customer.nin = nin
            customer.save(update_fields=["nin"])
            existing_nins.add(nin)
            updated_count += 1

            self.stdout.write(self.style.SUCCESS(f"Assigned NIN {nin} to {customer.full_name}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Done. Assigned NINs to {updated_count} customers."))