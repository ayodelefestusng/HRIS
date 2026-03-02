import random
import uuid
from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from org.models import Tenant, OrgUnit, Grade, JobRole
from employees.models import Employee, EmploymentStatus

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds 350 employees into DMC using custom User model and Unique Role logic."

    def handle(self, *args, **options):
        tenant = Tenant.objects.get(code="DMC")
        
        with transaction.atomic():
            # IMPORTANT: Clear existing data to avoid UNIQUE constraint failures on re-runs
            self.stdout.write("Wiping existing Employee and JobRole data for DMC...")
            JobRole.objects.filter(tenant=tenant).delete()
            Employee.objects.filter(tenant=tenant).delete()
            # Note: You might want to delete Users created for these employees too 
            # if they aren't linked elsewhere.

            # 1. Fetch Grades
            grades = {g.level: g for g in Grade.objects.filter(tenant=tenant)}
            
            # 2. Top-Level Hierarchy
            chairman_unit = OrgUnit.objects.get(code="CHM", tenant=tenant)
            chairman = self.create_emp(tenant, "Chairman", chairman_unit, grades[15], None, "M")

            md_unit = OrgUnit.objects.get(code="MD-O", tenant=tenant)
            md = self.create_emp(tenant, "Managing Director", md_unit, grades[14], chairman, "M")

            # 3. Directorate Heads (Reporting to MD)
            directorates = [
                ("BU", "Executive Director, Business", 13),
                ("BS", "Executive Director, Services", 13),
                ("FIN", "Head, Finance", 12),
                ("RC", "Head, Risk and Compliance", 12),
                ("BS-HR", "Head, Human Resources", 12),
            ]
            for code, title, lvl in directorates:
                unit = OrgUnit.objects.get(code=code, tenant=tenant)
                self.create_emp(tenant, title, unit, grades[lvl], md)

            # 4. Units & Branches
            all_units = OrgUnit.objects.filter(tenant=tenant).exclude(
                code__in=["CHM", "MD-O", "BU", "BS", "FIN", "RC", "BS-HR"]
            )
            
            target_staffed = 335 
            current_count = Employee.objects.filter(tenant=tenant).count()

            for unit in all_units:
                if current_count >= target_staffed: break
                
                # Assign Unit Head
                u_head = self.create_emp(tenant, f"Head, {unit.name}", unit, grades[random.randint(9, 11)], self.get_unit_head(unit.parent))
                current_count += 1

                # Staffing per unit
                num_staff = 15 if "SF-" in unit.code else random.randint(3, 6)
                for _ in range(num_staff):
                    if current_count >= target_staffed: break
                    role_name = "Sales Officer" if "SF-" in unit.code or "Branch" in unit.name else "Officer"
                    self.create_emp(tenant, role_name, unit, grades[random.randint(1, 7)], u_head)
                    current_count += 1

            # 5. Floating Staff (15)
            for _ in range(15):
                self.create_emp_floating(tenant, grades[random.randint(3, 7)])
                current_count += 1

            # 6. Apply 57 Allowances (7-18%)
            eligible_pool = list(Employee.objects.filter(tenant=tenant, grade__level__gte=3, grade__level__lte=13))
            if len(eligible_pool) >= 57:
                for emp in random.sample(eligible_pool, 57):
                    basic = float(emp.grade.basic_salary)
                    emp.above_grade_base_pay = int(basic * random.uniform(0.07, 0.18))
                    emp.save()

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {current_count} employees."))

    def create_emp(self, tenant, title, unit, grade, manager, gender=None):
        # ROLE LOGIC: Strict check for existing head in this unit
        is_head_title = any(kw in title for kw in ["Head", "Director", "Chairman", "MD"])
        head_exists = JobRole.objects.filter(org_unit=unit, role_type="HEAD", tenant=tenant).exists()

        if is_head_title and not head_exists:
            assigned_role_type = "HEAD"
        else:
            assigned_role_type = "MEMBER"
            if is_head_title: title = f"Deputy {title}"

        unique_id = uuid.uuid4().hex[:6].upper()
        email = f"staff_{unique_id}@dmc.com"
        f_name = "Ade" if (gender or "M") == "M" else "Bisi"
        l_name = "Ojo"

        # User creation matching your custom User model
        user = User.objects.create_user(
            email=email,
            full_name=f"{f_name} {l_name}",
            password="password123",
            tenant=tenant
        )
        
        emp = Employee.objects.create(
            tenant=tenant, user=user, employee_id=f"DMC-{unique_id}",
            employee_email=email, first_name=f_name, last_name=l_name,
            gender=gender or "M", date_of_birth=date(random.randint(1980, 2000), 1, 1),
            grade=grade, grade_base_pay=grade, line_manager=manager,
            national_id_number="".join([str(random.randint(0,9)) for _ in range(11)]),
            phone_number=f"0803{random.randint(1000000, 9999999)}",
            next_of_kin_phone_number=f"0817{random.randint(1000000, 9999999)}",
            emergency_contact_phone_number=f"0909{random.randint(1000000, 9999999)}",
            employment_status=EmploymentStatus.FULL_TIME
        )

        JobRole.objects.create(
            tenant=tenant, employee=emp, org_unit=unit, 
            designation=title, role_type=assigned_role_type
        )
        return emp

    def create_emp_floating(self, tenant, grade):
        unique_id = uuid.uuid4().hex[:6].upper()
        email = f"float_{unique_id}@dmc.com"
        user = User.objects.create_user(
            email=email, full_name="Floating Talent", 
            password="password123", tenant=tenant
        )
        Employee.objects.create(
            tenant=tenant, user=user, employee_id=f"DMC-FLT-{unique_id}",
            employee_email=email, first_name="Float", last_name="Staff",
            gender="M", date_of_birth=date(1995, 1, 1), grade=grade, grade_base_pay=grade,
            national_id_number="".join([str(random.randint(0,9)) for _ in range(11)]),
            phone_number=f"0703{random.randint(1000000, 9999999)}",
            next_of_kin_phone_number=f"0802{random.randint(1000000, 9999999)}",
            emergency_contact_phone_number=f"0808{random.randint(1000000, 9999999)}",
        )

    def get_unit_head(self, unit):
        if not unit: return None
        role = JobRole.objects.filter(org_unit=unit, role_type="HEAD").first()
        return role.employee if role else None