from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import capfirst
from org.models import Tenant  # Adjust based on your actual path
from org.models import OrgUnit # Adjust path
from org.models import JobRole, JobTitle # Adjust path
from django.core.exceptions import ObjectDoesNotExist
class Command(BaseCommand):
    help = "Generates and links JobTitles for the DMC tenant based on OrgUnit names and Role types."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        # 1. Fetch the DMC Tenant
        try:
            tenant = Tenant.objects.get(name="DMC")
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR("Tenant 'DMC' not found. Check the name in your database."))
            return

        self.stdout.write(f"Processing Job Titles for Tenant: {tenant.name}...")

        # 2. Map role types to their desired prefixes
        role_prefix_map = {
            "HEAD": "Head,",
            "DEPUTY": "Manager,",
            "MEMBER": "Officer,",
        }

        # 3. Fetch all roles for this tenant
        roles = JobRole.objects.filter(tenant=tenant, is_deleted=False)
        updated_count = 0
        created_titles = 0

        for role in roles:
            # Determine prefix (default to Officer if not found)
            prefix = role_prefix_map.get(role.role_type, "Officer,")
            
            # Format Org Unit Name to Title Case
            # .title() makes "ICT DEPARTMENT" -> "Ict Department"
            org_name_titled = role.org_unit.name.title()
            
            # Construct the Full Title Name
            full_title_name = f"{prefix} {org_name_titled}"

            # 4. Create Title Once & Link (get_or_create handles the 'unique=True' constraint)
            job_title_obj, created = JobTitle.objects.get_or_create(
                tenant=tenant,
                name=full_title_name,
                defaults={'description': f"Standardized title for {full_title_name}"}
            )

            if created:
                created_titles += 1

            # 5. Link the title to the Role
            role.job_title = job_title_obj
            role.save()
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done! Created {created_titles} new unique titles and updated {updated_count} roles."
        ))