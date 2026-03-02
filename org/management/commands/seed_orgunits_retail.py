from django.core.management.base import BaseCommand
from org.models import Tenant, Location, OrgUnit, Town

class Command(BaseCommand):
    help = "Seed OrgUnits hierarchy for Retail Management with CHQ, Regional Offices, Branches, and Sales Forces"

    def handle(self, *args, **options):
        try:
            tenant = Tenant.objects.get(code="3LN")
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR("Tenant not found"))
            return
#
        # --- Ensure Towns exist (exact names from DB) ---
        lagos_towns = ["Ikeja", "Lekki", "Lagos Island (Eko)", "Victoria Island"]
        kano_towns = ["Kano", "Kafanchan", "Kaduna"]
        abuja_towns = ["Abuja Municipal", "Wuse", "Garki", "Maitama", "Aba"]
        rivers_towns = ["Port Harcourt", "Abonnema"]

        for t in lagos_towns + kano_towns + abuja_towns + rivers_towns:
            Town.objects.get_or_create(name=t)

        # --- Corporate Head Office (CHQ) tied to Victoria Island ---
        chq, _ = Location.objects.get_or_create(
            tenant=tenant,
            name="Corporate Head Office",
            defaults={
                "location_id": "LOC-CHQ",
                "address": "Corporate HQ, Victoria Island",
                "town": Town.objects.get(name="Victoria Island")
            }
        )

        # --- Regional Offices ---
        lagos_RO, _ = Location.objects.get_or_create(
            tenant=tenant,
            name="Lagos Regional Office",
            defaults={
                "location_id": "LOC-LAG-RO",
                "address": "Regional Office, Lagos",
                "town": Town.objects.get(name="Victoria Island")
            }
        )
        abuja_RO, _ = Location.objects.get_or_create(
            tenant=tenant,
            name="Abuja Regional Office",
            defaults={
                "location_id": "LOC-ABJ-RO",
                "address": "Regional Office, Abuja",
                "town": Town.objects.get(name="Abuja Municipal")
            }
        )
        rivers_RO, _ = Location.objects.get_or_create(
            tenant=tenant,
            name="Rivers Regional Office",
            defaults={
                "location_id": "LOC-RIV-RO",
                "address": "Regional Office, Port Harcourt",
                "town": Town.objects.get(name="Port Harcourt")
            }
        )
        north_RO, _ = Location.objects.get_or_create(
            tenant=tenant,
            name="Northern Regional Office",
            defaults={
                "location_id": "LOC-NORTH-RO",
                "address": "Regional Office, Kano",
                "town": Town.objects.get(name="Kano")
            }
        )


        # --- Retail Management OrgUnit ---
        retail_mgmt, _ = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="BU-RM",
            defaults={"name": "Retail Management", "location": chq}
        )

        # --- Branch Network ---
        branch_network, _ = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="BU-RM-BN",
            defaults={"name": "Branch Network", "location": lagos_RO, "parent": retail_mgmt}
        )

        # --- Regional Offices and Branches ---
        regions = {
            "BN-REG-LAG": ("Regional Office (Lagos)", lagos_RO, "SF-LAG", "Sales Force – Lagos Region", lagos_towns),
            "BN-REG-ABJ": ("Regional Office (Abuja)", abuja_RO, "SF-ABJ", "Sales Force – Abuja Region", abuja_towns),
            "BN-REG-SOUTH": ("Regional Office (Rivers/South)", rivers_RO, "SF-SOUTH", "Sales Force – Southern Region", rivers_towns),
            "BN-REG-NORTH": ("Regional Office (North)", north_RO, "SF-NORTH", "Sales Force – Northern Region", kano_towns),
        }

        branch_counter = 1
        for region_code, (region_name, region_loc, sf_code, sf_name, towns) in regions.items():
            # Create Regional Office OrgUnit
            region_office, _ = OrgUnit.objects.get_or_create(
                tenant=tenant,
                code=region_code,
                defaults={"name": region_name, "location": region_loc, "parent": branch_network}
            )

            # Create Sales Force under Regional Office
            OrgUnit.objects.get_or_create(
                tenant=tenant,
                code=sf_code,
                defaults={"name": sf_name, "location": region_loc, "parent": region_office}
            )

            # Create Branches under Regional Office
            for town_name in towns:
                branch_code = f"BN-{branch_counter:04d}"
                town_obj, _ = Town.objects.get_or_create(name=town_name)
                branch_loc, _ = Location.objects.get_or_create(
                    tenant=tenant,
                    name=f"{town_name} Branch Location",
                    defaults={
                        "location_id": branch_code,
                        "address": f"{town_name}, Nigeria",
                        "town": town_obj,
                    }
                )
                OrgUnit.objects.get_or_create(
                    tenant=tenant,
                    code=branch_code,
                    defaults={
                        "name": f"{town_name} Branch",
                        "location": branch_loc,
                        "parent": region_office,
                    }
                )
                branch_counter += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded Retail Management hierarchy with Branch Network, 4 Regional Offices, Branches tied to real Towns, and Regional Sales Forces"
            )
        )