from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from rbac.models import Role, Permission
from django.db import transaction

class Command(BaseCommand):
    help = 'Setup initial User Groups and RBAC Roles'

    def handle(self, *args, **kwargs):
        roles_data = {
            "Employee": "General staff access",
            "HR Officer": "Handles HR activities (ATS, Org Units, Payroll)",
            "Manager": "Supervises employees, approves tasks",
            "HR Manager": "Approves tasks raised by HR Officers",
            "HR Admin": "Super admin with combined powers",
        }

        with transaction.atomic():
            for role_name, description in roles_data.items():
                # 1. Create or Update Django Group
                group, created = Group.objects.get_or_create(name=role_name)
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created Group: {role_name}'))
                else:
                    self.stdout.write(f'Group already exists: {role_name}')

                # 2. Create or Update RBAC Role (Custom Model)
                # Note: Assuming RBAC Role model is not strictly tied to Django Group 1-to-1 in code, 
                # but we want them to mirror each other for this setup.
                role, created = Role.objects.get_or_create(name=role_name, defaults={'description': description})
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created RBAC Role: {role_name}'))
                else:
                    # Update description if it changed
                    if role.description != description:
                        role.description = description
                        role.save()
                        self.stdout.write(f'Updated RBAC Role setup: {role_name}')
                    else:
                        self.stdout.write(f'RBAC Role already exists: {role_name}')

        self.stdout.write(self.style.SUCCESS('Successfully completed roles and groups setup'))
