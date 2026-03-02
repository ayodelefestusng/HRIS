import random
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from org.models import Tenant, Location
from employees.models import Unit
from ats.models import JobPosting, Candidate, Application
from org.models import OrgUnit

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seeds the database with tenants and 12 ATS samples per tenant'

    TENANT_DATA = [
        {"name": "Default Tenant", "code": "Default-0001", "subdomain": "default-tenant", "is_active": True},
        {"name": "3Line", "code": "3LINE_0001", "subdomain": "3line", "is_active": True},
        {"name": "NewGold", "code": "NEWG", "subdomain": "newgold", "is_active": True},
        {"name": "TopMost", "code": "TOPM", "subdomain": "topmost", "is_active": True},
        {"name": "ATB", "code": "ATB", "subdomain": "atb", "is_active": True},
        {"name": "BuildBank", "code": "BLDB", "subdomain": "buildbank", "is_active": True}
    ]

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting seeding process...")

        for t_data in self.TENANT_DATA:
            # 1. Create or Get Tenant
            tenant, created = Tenant.objects.get_or_create(
                code=t_data['code'],
                defaults={
                    'name': t_data['name'],
                    'subdomain': t_data['subdomain'],
                    'is_active': t_data['is_active']
                }
            )
            
            # 2. Setup Prerequisites for the Tenant
            unit, _ = OrgUnit.objects.get_or_create(name="Human Resources", tenant=tenant)
            location, _ = Location.objects.get_or_create(name="Head Office", tenant=tenant)

            # 3. Create a Job Posting
            job, _ = JobPosting.objects.get_or_create(
                title=f"Senior Developer - {tenant.code}",
                tenant=tenant,
                defaults={
                    'unit': unit,
                    'description': "Seed job description",
                    'requirements': "Seed requirements",
                    'status': 'OPEN',
                    'closing_date': timezone.now().date()
                }
            )
            job.locations.add(location)

            # 4. Create 12 Candidates and Applications
            for i in range(1, 13):
                email = f"candidate{i}@{tenant.subdomain}.com"
                
                # Create Candidate
                candidate, _ = Candidate.objects.get_or_create(
                    email=email,
                    tenant=tenant,
                    defaults={
                        'full_name': f"Candidate {i} for {tenant.name}",
                        'phone': f"0800-{tenant.code}-{i:03d}",
                        'notes': f"Seeded candidate for {tenant.name}"
                    }
                )

                # Create Application
                status_list = ["APPLIED", "INTERVIEW", "OFFER", "HIRED", "REJECTED"]
                Application.objects.get_or_create(
                    candidate=candidate,
                    job_posting=job,
                    tenant=tenant,
                    defaults={
                        'status': random.choice(status_list)
                    }
                )

            self.stdout.write(self.style.SUCCESS(f"Successfully seeded 12 candidates for {tenant.name}"))

        self.stdout.write(self.style.SUCCESS("Seeding Complete!"))