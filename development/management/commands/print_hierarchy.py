import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from employees.models import Employee  # Adjust based on your app name
from workflow.services.dashboard_service import WorkflowService  # Assuming WorkflowService is here

class Command(BaseCommand):
    help = "Prints detailed hierarchy and sets superuser status for the entire chain"

    def handle(self, *args, **options):
        target_email = "rose.aminu.okeke@dignityconcept.tech"
        service = WorkflowService()
        
        try:
            # 1. Fetch Primary Target
            target_emp = Employee.objects.get(employee_email=target_email)
            
            # 2. Identify all people in the "Chain of Influence"
            # Includes: Grand Manager, Direct Manager, Target, and all recursive subordinates
            line_manager = target_emp.line_manager
            grand_manager = line_manager.line_manager if line_manager else None
            
            all_involved = []
            if grand_manager: all_involved.append(grand_manager)
            if line_manager and line_manager not in all_involved: all_involved.append(line_manager)
            
            # Get all recursive subordinates (including target)
            downline_ids = service.get_recursive_downline_ids(target_emp)
            subordinates_list = Employee.objects.filter(id__in=downline_ids)
            all_involved.extend(list(subordinates_list))

            # Remove duplicates while preserving order
            seen = set()
            unique_involved = [x for x in all_involved if not (x.id in seen or seen.add(x.id))]

            # 3. Process each employee
            for emp in unique_involved:
                self.process_and_print_employee(emp, service)

            self.stdout.write(self.style.SUCCESS("\nAll listed users upgraded to Superuser with password @Ajibandele1"))

        except Employee.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Target {target_email} not found."))

    def process_and_print_employee(self, emp, service):
        """Calculates stats, upgrades user, and prints in requested format."""
        
        # --- Superuser Upgrade Logic ---
        user = emp.user
        if user:
            user.is_superuser = True
            user.is_staff = True
            user.set_password("@Ajibandele1")
            user.save()

        # --- Hierarchy Calculations ---
        depth = 1
        curr = emp
        while curr.line_manager:
            depth += 1
            curr = curr.line_manager
        
        direct_manager = emp.line_manager
        grand_manager = direct_manager.line_manager if direct_manager else None
        
        # Get immediate subordinates only for the count display
        direct_subordinates = Employee.objects.filter(line_manager=emp)
        sub_names = ", ".join([s.full_name for s in direct_subordinates]) if direct_subordinates.exists() else "None"
        
        # --- Final Print Formatting ---
        status = "ACTIVE" if (user and user.is_active) else "INACTIVE"
        
        output = [
            f"NAME: {emp.full_name} (SUPERUSER STATUS: {status})",
            f"DEPTH: {depth}",
            f"EMAIL: {emp.employee_email}",
            f"ROLE: {getattr(emp, 'job_role', 'Staff')}",
            f"DIRECT MANAGER: {direct_manager.full_name if direct_manager else 'N/A'}",
            f"GRAND MANAGER: {grand_manager.full_name if grand_manager else 'N/A'}",
            f"SUBORDINATES ({direct_subordinates.count()}): {sub_names}",
            "-" * 50
        ]
        
        self.stdout.write("\n".join(output))