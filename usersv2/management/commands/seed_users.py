from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from org.models import Tenant

User = get_user_model()

class Command(BaseCommand):
    help = "Seed initial users with tenants"

    def handle(self, *args, **options):
        seeds = [
            {
                "email": "ayodelefestusng@gmail.com",
                "full_name": "Ayodele Adeyinka",
                "is_superuser": True,
                "is_staff": True,
                "tenant": None,
            },
            {
                "email": "upwardwave.dignity@gmail.com",
                "full_name": "Dignity",
                "is_superuser": True,
                "is_staff": True,
                "tenant_code": "DMC",
            },
            {
                "email": "ryisa@gmail.com",
                "full_name": "Raliat",
                "tenant_code": "RAN",  # RealAnalytics
            },
            {
                "email": "fegunjobi@gmail.com",
                "full_name": "Folake",
                "tenant_code": "RVX",  # Ravexta
            },
            {
                "email": "aatobatele@gmail.com",
                "full_name": "Abiodun",
                "tenant_code": "ATB",
            },
        ]

        for data in seeds:
            tenant = None
            if "tenant_code" in data:
                try:
                    tenant = Tenant.objects.get(code=data["tenant_code"])
                except Tenant.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Tenant {data['tenant_code']} not found"))
                    continue

            user, created = User.objects.get_or_create(
                email=data["email"],
                defaults={
                    "full_name": data.get("full_name"),
                    "tenant": tenant,
                    "is_superuser": data.get("is_superuser", False),
                    "is_staff": data.get("is_staff", False),
                },
            )
            if created:
                user.set_password("@Ajibandele1")  # default password
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created user {user.email}"))
            else:
                self.stdout.write(self.style.WARNING(f"User already exists: {user.email}"))