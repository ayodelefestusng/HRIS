from django.core.management.base import BaseCommand
from django.db import transaction
from org.models import Tenant, Location, OrgUnit

class Command(BaseCommand):
    help = "Seeds the multi-level OrgUnit hierarchy for DMC."

    def handle(self, *args, **options):
        try:
            tenant = Tenant.objects.get(code="DMC")
            chq = Location.objects.get(location_id="LOC-CHQ")
        except (Tenant.DoesNotExist, Location.DoesNotExist):
            self.stderr.write("Tenant 'DMC' or 'LOC-CHQ' missing. Seed locations first.")
            return

        with transaction.atomic():
            # 1. Level 0: Chairman
            chairman, _ = OrgUnit.objects.get_or_create(
                tenant=tenant, code="CHM",
                defaults={"name": "Chairman Office", "location": chq}
            )

            # 2. Level 1: MD Office
            md_office, _ = OrgUnit.objects.get_or_create(
                tenant=tenant, code="MD-O",
                defaults={"name": "MD's Office", "location": chq, "parent": chairman}
            )

            # 3. Level 2: Core Directorates
            business_unit, _ = OrgUnit.objects.get_or_create(
                tenant=tenant, code="BU",
                defaults={"name": "Business Unit", "location": chq, "parent": md_office}
            )
            business_services, _ = OrgUnit.objects.get_or_create(
                tenant=tenant, code="BS",
                defaults={"name": "Business Services", "location": chq, "parent": md_office}
            )
            risk_compliance, _ = OrgUnit.objects.get_or_create(
                tenant=tenant, code="RC",
                defaults={"name": "Risk and Compliance", "location": chq, "parent": md_office}
            )
            finance_unit, _ = OrgUnit.objects.get_or_create(
                tenant=tenant, code="FIN",
                defaults={"name": "Finance", "location": chq, "parent": md_office}
            )

            # 4. Level 3 & 4: Deep Dive - Business Services (Using Prefix logic)
            # HR, Tech, Legal, Operations
            hr_dept, _ = OrgUnit.objects.get_or_create(
                tenant=tenant, code="BS-HR",
                defaults={"name": "Human Resources", "location": chq, "parent": business_services}
            )
            for sub in [("Payroll", "PAY"), ("Recruitment", "REC"), ("Training & Development", "TAD")]:
                OrgUnit.objects.get_or_create(
                    tenant=tenant, code=f"BS-HR-{sub[1]}",
                    defaults={"name": sub[0], "location": chq, "parent": hr_dept}
                )

            tech_dept, _ = OrgUnit.objects.get_or_create(
                tenant=tenant, code="BS-IT",
                defaults={"name": "Technology", "location": chq, "parent": business_services}
            )
            for sub in [("Digital Solution", "DS"), ("IT Infrastructure", "INF")]:
                OrgUnit.objects.get_or_create(
                    tenant=tenant, code=f"BS-IT-{sub[1]}",
                    defaults={"name": sub[0], "location": chq, "parent": tech_dept}
                )

            # 5. Level 3: Retail Management & Branch Network
            retail_mgmt, _ = OrgUnit.objects.get_or_create(
                tenant=tenant, code="BU-RM",
                defaults={"name": "Retail Management", "location": chq, "parent": business_unit}
            )
            branch_network, _ = OrgUnit.objects.get_or_create(
                tenant=tenant, code="BU-RM-BN",
                defaults={"name": "Branch Network", "location": chq, "parent": retail_mgmt}
            )

            # 6. Level 4 & 5: Regional Offices, Sales Forces, and Branches
            regions = {
                "BN-REG-LAG": {
                    "name": "Lagos Regional Office", 
                    "loc": Location.objects.get(location_id="LOC-LAG-RO"), 
                    "sf": "SF-LAG", 
                    "sf_name": "Sales Force – Lagos Region",
                    "towns": ["Ikeja", "Lekki", "Lagos Island (Eko)"]
                },
                "BN-REG-ABJ": {
                    "name": "Abuja Regional Office", 
                    "loc": Location.objects.get(location_id="LOC-ABJ-RO"), 
                    "sf": "SF-ABJ", 
                    "sf_name": "Sales Force – Abuja Region",
                    "towns": ["Wuse", "Garki", "Maitama", "Aba"]
                },
                "BN-REG-NORTH": {
                    "name": "Northern Regional Office", 
                    "loc": Location.objects.get(location_id="LOC-NORTH-RO"), 
                    "sf": "SF-NORTH", 
                    "sf_name": "Sales Force – Northern Region",
                    "towns": ["Kaduna", "Kafanchan"]
                },
                "BN-REG-SOUTH": {
                    "name": "Rivers Regional Office", 
                    "loc": Location.objects.get(location_id="LOC-RIV-RO"), 
                    "sf": "SF-SOUTH", 
                    "sf_name": "Sales Force – Southern Region",
                    "towns": ["Abonnema"]
                },
            }

            for r_code, data in regions.items():
                # Create RO Unit
                ro_unit, _ = OrgUnit.objects.get_or_create(
                    tenant=tenant, code=r_code,
                    defaults={"name": data["name"], "location": data["loc"], "parent": branch_network}
                )

                # Create SF Unit under RO
                OrgUnit.objects.get_or_create(
                    tenant=tenant, code=data["sf"],
                    defaults={"name": data["sf_name"], "location": data["loc"], "parent": ro_unit}
                )

                # Create physical Branches under RO
                for town in data["towns"]:
                    try:
                        branch_loc = Location.objects.get(name=f"{town} Branch Location", tenant=tenant)
                        OrgUnit.objects.get_or_create(
                            tenant=tenant, code=branch_loc.location_id,
                            defaults={
                                "name": f"{town} Branch",
                                "location": branch_loc,
                                "parent": ro_unit
                            }
                        )
                    except Location.DoesNotExist:
                        continue

        self.stdout.write(self.style.SUCCESS("OrgUnit Hierarchy successfully seeded!"))