from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Master seed script to populate the database with initial data (Tenants, Users, Org, Employees, ATS)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting Master Database Seeding..."))

        try:
            with transaction.atomic():
                # 1. Tenants
                self.stdout.write("--> Seeding Tenants...")
                call_command("create_default_tenant")

                # 2. Users
                self.stdout.write("--> Seeding Users...")
                call_command("seed_users")

                # 3. Organization Units (Retail Structure)
                self.stdout.write("--> Seeding Org Units (Retail)...")
                call_command("seed_orgunits_retail")

                # 4. HR Data (Grades, Employees, Payroll structure)
                self.stdout.write("--> Seeding HR Data...")
                call_command("seed_hr")

                # 5. ATS Data (Jobs, Candidates, Applications)
                self.stdout.write("--> Seeding ATS Data...")
                call_command("seed_ats")

                self.stdout.write(
                    self.style.SUCCESS("GRAND SUCCESS: Database seeded successfully!")
                )

        except Exception as e:
            logger.error(f"Seeding failed: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Seeding Failed: {str(e)}"))
            # Transaction atomic will rollback changes
