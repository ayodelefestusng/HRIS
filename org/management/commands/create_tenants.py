from django.core.management.base import BaseCommand
from org.models import Tenant

class Command(BaseCommand):
    help = "Create predefined tenants: DMC, 3line, Ravexta, ATB, RealAnalytics"

    def handle(self, *args, **options):
        tenants = [
            {"name": "DMC", "code": "DMC", "subdomain": "dmc"},
            {"name": "3line", "code": "3LN", "subdomain": "3line"},
            {"name": "Ravexta", "code": "RVX", "subdomain": "ravexta"},
            {"name": "ATB", "code": "ATB", "subdomain": "atb"},
            {"name": "RealAnalytics", "code": "RAN", "subdomain": "realanalytics"},
        ]

        for tenant_data in tenants:
            tenant, created = Tenant.objects.get_or_create(
                code=tenant_data["code"],
                defaults={
                    "name": tenant_data["name"],
                    "subdomain": tenant_data["subdomain"],
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created tenant: {tenant}"))
            else:
                self.stdout.write(self.style.WARNING(f"Tenant already exists: {tenant}"))