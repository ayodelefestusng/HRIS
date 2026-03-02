from django.core.management.base import BaseCommand
from django.db import transaction
from org.models import Tenant, Town, Location

class Command(BaseCommand):
    help = "Seeds CHQ, Regional Offices, and an expanded Branch network for DMC."

    def handle(self, *args, **options):
        try:
            tenant = Tenant.objects.get(code="DMC")
        except Tenant.DoesNotExist:
            self.stderr.write("Tenant 'DMC' not found.")
            return

        # Updated Geography Data for the new towns
        geo_data = {
            "Victoria Island": (6.4281, 3.4215),
            "Ikeja": (6.6018, 3.3515),
            "Surulere": (6.5059, 3.3484),
            "Oyo": (7.8430, 3.9368),
            "Lekki": (6.4698, 3.5852),
            "Lagos Island (Eko)": (6.4549, 3.3887),
            "Abeokuta": (7.1475, 3.3619),
            "Akure": (7.2571, 5.2058),
            "Abuja Municipal": (9.0578, 7.4951),
            "Suleja": (9.1806, 7.1794),
            "Asokoro": (9.0390, 7.5185),
            "Lafia": (8.4912, 8.5204),
            "Keffi": (8.8476, 7.8735),
            "Port Harcourt": (4.8156, 7.0498),
            "Benin City": (6.3350, 5.6037),
            "Asaba": (6.2018, 6.6941),
            "Owerri": (5.4850, 7.0350),
            "Awka": (6.2105, 7.0722),
            "Kano": (12.0022, 8.5920),
            "Kaduna": (10.5105, 7.4165),
            "Sokoto": (13.0059, 5.2476),
            "Maiduguri": (11.8311, 13.1510),
            "Gombe": (10.2841, 11.1673),
            "Wudil": (11.8106, 8.8436),
        }

        with transaction.atomic():
            self.stdout.write("Creating Primary Hubs and Branch categories...")

            # 1. Corporate Head Office (Logical) and its Branch
            vi_town = Town.objects.get(name="Victoria Island")
            chq, _ = Location.objects.update_or_create(
                tenant=tenant, location_id="LOC-CHQ",
                defaults={"name": "Corporate Head Office", "address": "HQ, Victoria Island", "town": vi_town}
            )
            Location.objects.update_or_create(
                tenant=tenant, location_id="BN-CHQ",
                defaults={"name": "CHQ Branch", "address": "CHQ Banking Hall, VI", "town": vi_town}
            )

            # 2. Regional Offices and their corresponding Branches
            # Structure: (Region Name, ID, RO_ID, Town Name)
            regions = [
                ("Lagos", "LAG", "Victoria Island"),
                ("Abuja", "ABJ", "Abuja Municipal"),
                ("Rivers", "RIV", "Port Harcourt"),
                ("Northern", "NORTH", "Kano"),
            ]

            for reg_name, reg_id, town_name in regions:
                town_obj = Town.objects.get(name=town_name)
                lat, lon = geo_data.get(town_name, (None, None))
                
                # The RO Admin Hub
                Location.objects.update_or_create(
                    tenant=tenant, location_id=f"LOC-{reg_id}-RO",
                    defaults={"name": f"{reg_name} Regional Office", "address": f"Regional HQ, {town_name}", "town": town_obj, "latitude": lat, "longitude": lon}
                )
                # The RO Service Branch
                Location.objects.update_or_create(
                    tenant=tenant, location_id=f"BN-{reg_id}-RO",
                    defaults={"name": f"{reg_name} RO Branch", "address": f"Regional Branch Hall, {town_name}", "town": town_obj, "latitude": lat, "longitude": lon}
                )

            # 3. Additional Network Branches across listed towns
            self.stdout.write("Seeding additional town-specific branches...")
            branch_networks = {
                "Lagos": ["Surulere", "Oyo", "Lekki", "Lagos Island (Eko)", "Abeokuta", "Akure"],
                "Abuja": ["Abuja Municipal", "Suleja", "Asokoro", "Lafia", "Keffi"],
                "Rivers": ["Benin City", "Asaba", "Owerri", "Awka", "Port Harcourt"],
                "Northern": ["Kaduna", "Sokoto", "Maiduguri", "Gombe", "Wudil"],
            }

            branch_counter = 1
            for region, towns in branch_networks.items():
                for t_name in towns:
                    # Skip if it's already a primary RO town (to avoid ID conflicts)
                    town_obj = Town.objects.get(name=t_name)
                    lat, lon = geo_data.get(t_name, (None, None))
                    
                    Location.objects.update_or_create(
                        tenant=tenant, name=f"{t_name} Branch Location",
                        defaults={
                            "location_id": f"BN-EXT-{branch_counter:04d}",
                            "address": f"{t_name} Town Centre",
                            "town": town_obj,
                            "latitude": lat,
                            "longitude": lon
                        }
                    )
                    branch_counter += 1

        self.stdout.write(self.style.SUCCESS(f"Locations amended: Hubs, RO Branches, and {branch_counter-1} external branches created."))