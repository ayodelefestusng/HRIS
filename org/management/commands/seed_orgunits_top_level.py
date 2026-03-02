from django.core.management.base import BaseCommand
from org.models import Tenant, Location, OrgUnit, Town

class Command(BaseCommand):
    help = "Seed full OrgUnits hierarchy for Tenant 3Line with CHQ and Regional Offices"

    def handle(self, *args, **options):
        try:
            tenant = Tenant.objects.get(code="3LN")
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR("Tenant not found"))
            return

        # --- Ensure Towns exist ---
        chq_town, _ = Town.objects.get_or_create(name="Victoria Island")
        lagos_town, _ = Town.objects.get_or_create(name="Ikeja")
        abuja_town, _ = Town.objects.get_or_create(name="Abuja Municipal")
        rivers_town, _ = Town.objects.get_or_create(name="Port Harcourt")
        north_town, _ = Town.objects.get_or_create(name="Kano")

        # --- Corporate Head Office (CHQ) ---
        chq, _ = Location.objects.get_or_create(
            tenant=tenant,
            name="Corporate Head Office",
            defaults={"location_id": "LOC-CHQ", "address": "Corporate HQ, Victoria Island", "town": chq_town}
        )

        # --- Regional Offices ---
        lagos_RO, _ = Location.objects.get_or_create(
            tenant=tenant,
            name="Lagos Regional Office",
            defaults={"location_id": "LOC-LAG-RO", "address": "Regional Office, Lagos", "town": lagos_town}
        )
        abuja_RO, _ = Location.objects.get_or_create(
            tenant=tenant,
            name="Abuja Regional Office",
            defaults={"location_id": "LOC-ABJ-RO", "address": "Regional Office, Abuja", "town": abuja_town}
        )
        rivers_RO, _ = Location.objects.get_or_create(
            tenant=tenant,
            name="Rivers Regional Office",
            defaults={"location_id": "LOC-RIV-RO", "address": "Regional Office, Port Harcourt", "town": rivers_town}
        )
        north_RO, _ = Location.objects.get_or_create(
            tenant=tenant,
            name="Northern Regional Office",
            defaults={"location_id": "LOC-NORTH-RO", "address": "Regional Office, Kano", "town": north_town}
        )

        # --- MD’s Office ---
        md_office, _ = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="MD",
            defaults={"name": "MD’s Office", "location": chq},
        )

        # --- Business Unit ---
        bu, _ = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="BU",
            defaults={"name": "Business Unit", "location": chq, "parent": md_office},
        )

        # Sub-units under Business Unit
        bu_pm, _ = OrgUnit.objects.get_or_create(tenant=tenant, code="BU-PM",
            defaults={"name": "Product Management", "location": chq, "parent": bu})
        bu_rm, _ = OrgUnit.objects.get_or_create(tenant=tenant, code="BU-RM",
            defaults={"name": "Retail Management", "location": chq, "parent": bu})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BU-RM-BN",
            defaults={"name": "Branch Network", "location": lagos_RO, "parent": bu_rm})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BU-RM-CE",
            defaults={"name": "Client Engagement", "location": chq, "parent": bu_rm})

        bu_ka, _ = OrgUnit.objects.get_or_create(tenant=tenant, code="BU-KA",
            defaults={"name": "Key Accounts", "location": chq, "parent": bu})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BU-KA-FA",
            defaults={"name": "Franchise & Alliances", "location": chq, "parent": bu_ka})

        OrgUnit.objects.get_or_create(tenant=tenant, code="BU-SALES",
            defaults={"name": "Sales (Business Development)", "location": chq, "parent": bu})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BU-SUB",
            defaults={"name": "Subsidiaries", "location": chq, "parent": bu})

        # --- Business Services ---
        bs, _ = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="BS",
            defaults={"name": "Business Services", "location": chq, "parent": md_office},
        )

        bs_cps, _ = OrgUnit.objects.get_or_create(tenant=tenant, code="BS-CPS",
            defaults={"name": "Corporate Planning & Strategy", "location": chq, "parent": bs})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-CPS-INN",
            defaults={"name": "Innovation", "location": chq, "parent": bs_cps})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-CPS-BIA",
            defaults={"name": "Business Intelligence & Analytics", "location": chq, "parent": bs_cps})

        bs_ops, _ = OrgUnit.objects.get_or_create(tenant=tenant, code="BS-OPS",
            defaults={"name": "Operations", "location": chq, "parent": bs})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-OPS-PC",
            defaults={"name": "Payments & Clearing", "location": chq, "parent": bs_ops})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-OPS-BOP",
            defaults={"name": "Back Office Processing", "location": chq, "parent": bs_ops})

        bs_tech, _ = OrgUnit.objects.get_or_create(tenant=tenant, code="BS-TECH",
            defaults={"name": "Technology", "location": chq, "parent": bs})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-TECH-DS",
            defaults={"name": "Digital Solution", "location": chq, "parent": bs_tech})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-TECH-IT",
            defaults={"name": "IT Infrastructure", "location": chq, "parent": bs_tech})

        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-LEGAL",
            defaults={"name": "Legal", "location": chq, "parent": bs})

        bs_ca, _ = OrgUnit.objects.get_or_create(tenant=tenant, code="BS-CA",
            defaults={"name": "Corporate Affairs", "location": chq, "parent": bs})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-CA-CB",
            defaults={"name": "Communication & Brand", "location": chq, "parent": bs_ca})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-CA-PRO",
            defaults={"name": "Protocol", "location": chq, "parent": bs_ca})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-CA-FM",
            defaults={"name": "Facility Management", "location": chq, "parent": bs_ca})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-CA-VM",
            defaults={"name": "Vendor Management", "location": chq, "parent": bs_ca})

        bs_hr, _ = OrgUnit.objects.get_or_create(tenant=tenant, code="BS-HR",
            defaults={"name": "Human Resources", "location": chq, "parent": bs})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-HR-PR",
            defaults={"name": "Payroll", "location": chq, "parent": bs_hr})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-HR-REC",
            defaults={"name": "Recruitment", "location": chq, "parent": bs_hr})
        OrgUnit.objects.get_or_create(tenant=tenant, code="BS-HR-TD",
            defaults={"name": "Training & Development", "location": chq, "parent": bs_hr})

        # --- Risk & Compliance ---
        rc, _ = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="RC",
            defaults={"name": "Risk & Compliance", "location": chq, "parent": md_office},
        )
        OrgUnit.objects.get_or_create(tenant=tenant, code="RC-ICC",
            defaults={"name": "Internal Control & Compliance", "location": chq, "parent": rc})
        OrgUnit.objects.get_or_create(tenant=tenant, code="RC-AUD",
            defaults={"name": "Audit", "location": chq, "parent": rc})
        OrgUnit.objects.get_or_create(tenant=tenant, code="RC-OR",
            defaults={"name": "Operational Risk", "location": chq, "parent": rc})
        OrgUnit.objects.get_or_create(tenant=tenant, code="RC-CS",
            defaults={"name": "Cyber Security ", "location": chq, "parent": rc})
        
        # --- Finance ---
        fin, _ = OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="FIN",
            defaults={"name": "Finance", "location": chq, "parent": md_office},
        )

        OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="FIN-SR",
            defaults={"name": "Settlement & Reconciliation", "location": chq, "parent": fin},
        )

        OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="FIN-ALM",
            defaults={"name": "Asset & Liability Management", "location": chq, "parent": fin},
        )

        OrgUnit.objects.get_or_create(
            tenant=tenant,
            code="FIN-FRB",
            defaults={"name": "Financial Reporting & Budgeting", "location": chq, "parent": fin},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Seedd Org Top Elevel Org Unit s"
            )
        )