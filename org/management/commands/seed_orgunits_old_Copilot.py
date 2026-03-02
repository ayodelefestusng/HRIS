from django.core.management.base import BaseCommand
from org.models import Tenant, OrgUnit, Location

class Command(BaseCommand):
    help = "Seed OrgUnit hierarchy for tenant 3Line"

    def handle(self, *args, **options):
        try:
            tenant = Tenant.objects.get(code="3LN")  # 👈 adjust to your tenant code
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR("Tenant 3Line not found"))
            return

        # Helper to fetch location
        def get_location(loc_id):
            try:
                return Location.objects.get(location_id=loc_id)
            except Location.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Location {loc_id} not found"))
                return None

        # Create hierarchy
        mds_office = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="010000000",
            defaults={
                "name": "MDs Office",
                "location": get_location("001"),
                "depth": 0,
                "parent": None,
            },
        )[0]

        consumer_dir = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="011000000",
            defaults={
                "name": "Consumer Bank Directorate",
                "location": get_location("001"),
                "depth": 1,
                "parent": mds_office,
            },
        )[0]

        consumer_bank = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="011100000",
            defaults={
                "name": "Consumer Bank",
                "location": get_location("001"),  # or create Lagos/Ikoyi Island location
                "depth": 2,
                "parent": consumer_dir,
            },
        )[0]

        consumer_distribution = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="011100000",
            defaults={
                "name": "Consumer Distribution",
                "location": get_location("009A"),
                "depth": 2,
                "parent": consumer_dir,
            },
        )[0]

        digital_banking = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="011110000",
            defaults={
                "name": "Digital Banking",
                "location": get_location("009A"),
                "depth": 3,
                "parent": consumer_distribution,
            },
        )[0]

        atm_business = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="011111000",
            defaults={
                "name": "ATM Business",
                "location": get_location("009A"),
                "depth": 3,
                "parent": digital_banking,
            },
        )[0]

        atm_monitoring = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="011111000",
            defaults={
                "name": "ATM Monitoring",
                "location": get_location("009A"),
                "depth": 4,
                "parent": atm_business,
            },
        )[0]

        self.stdout.write(self.style.SUCCESS("Seeded OrgUnits for tenant 3Line"))