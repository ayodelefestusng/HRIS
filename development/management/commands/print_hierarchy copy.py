import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from employees.models import Employee  # Adjust based on your app name
from workflow.services.dashboard_service import WorkflowService  # Assuming WorkflowService is here

class Command(BaseCommand):
    help = "Prints hierarchy details and upgrades users to superuser"

    def handle(self, *args, **options):
        target_email = "rose.aminu.okeke@dignityconcept.tech"
        service = WorkflowService()
        
        try:
            # 1. Fetch the Target Employee
            target_emp = Employee.objects.get(employee_email=target_email)
            
            # 2. Get Managers
            line_manager = target_emp.line_manager
            grand_manager = line_manager.line_manager if line_manager else None
            
            # 3. Get Downlines (Recursive)
            downline_ids = service.get_recursive_downline_ids(target_emp)
            # Remove self from subordinates list for the print count
            subordinate_ids = [eid for eid in downline_ids if eid != target_emp.id]
            subordinates = Employee.objects.filter(id__in=subordinate_ids)
            
            # 4. Calculate Depth (Climbing Up)
            depth = 1
            curr = target_emp
            while curr.line_manager:
                depth += 1
                curr = curr.line_manager
            
            # 5. Upgrade All to Superuser
            involved_employees = [target_emp]
            if line_manager: involved_employees.append(line_manager)
            if grand_manager: involved_employees.append(grand_manager)
            involved_employees.extend(list(subordinates))
            
            for emp in involved_employees:
                user = emp.user
                if user:
                    user.is_superuser = True
                    user.is_staff = True
                    # Set the requested password
                    user.set_password("@Ajibandele1")
                    user.save()

            # 6. Final Print Output
            status = "ACTIVE" if target_emp.user.is_active else "INACTIVE"
            self.stdout.write("-" * 40)
            self.stdout.write(f"NAME: {target_emp.full_name} (SUPERUSER STATUS: {status})")
            self.stdout.write(f"DEPTH: {depth}")
            self.stdout.write(f"EMAIL: {target_emp.personal_email}")
            self.stdout.write(f"ROLE: {target_emp.job_role if hasattr(target_emp, 'job_role') else 'N/A'}")
            self.stdout.write(f"DIRECT MANAGER: {line_manager.full_name if line_manager else 'None'}")
            self.stdout.write(f"GRAND MANAGER: {grand_manager.full_name if grand_manager else 'None'}")
            
            sub_list = ", ".join([s.full_name for s in subordinates]) if subordinates.exists() else "None"
            self.stdout.write(f"SUBORDINATES ({subordinates.count()}): {sub_list}")
            self.stdout.write("-" * 40)
            self.stdout.write(self.style.SUCCESS("Successfully upgraded all hierarchy members to Superuser."))

        except Employee.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Employee {target_email} not found."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {str(e)}"))