from django.core.management.base import BaseCommand
from org.models import Tenant

class Command(BaseCommand):
    help = "Create a default tenant with code Default-0001"

    def handle(self, *args, **options):
        tenant_code = "Default-0001"
        tenant_name = "Default Tenant"
        tenant_subdomain = "default"

        # Check if tenant already exists
        if Tenant.objects.filter(code=tenant_code).exists():
            self.stdout.write(self.style.WARNING(
                f"Tenant with code '{tenant_code}' already exists."
            ))
            return

        # Create the tenant
        tenant = Tenant.objects.create(
            name=tenant_name,
            code=tenant_code,
            subdomain=tenant_subdomain,
            is_active=True
        )

        self.stdout.write(self.style.SUCCESS(
            f"Default tenant created successfully: {tenant.name} ({tenant.code})"
        ))