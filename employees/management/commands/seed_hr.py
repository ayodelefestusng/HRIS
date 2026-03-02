import random
from faker import Faker
from django.core.management.base import BaseCommand
from org.models import Tenant, Grade
from payroll.models import GradeAllowance, AllowanceType
from ats.models import Application, Interview, InterviewFeedback
from employees.models import Employee
from users.models import User

fake = Faker()

class Command(BaseCommand):
    help = "Seed Grades, Employees, Applications, and Interviews for Tenant 3Line"

    def handle(self, *args, **options):
        tenant = Tenant.objects.get(code="3LN")  # Tenant 3Line

        # Executive allowances
        executive_allowances = {
            11: {"Housing": 200000, "Car": 150000, "Utility": 50000},
            12: {"Housing": 300000, "Car": 200000, "Utility": 75000},
            13: {"Housing": 500000, "Car": 300000, "Utility": 100000},
        }

        # Allowance types
        allowance_types = [
            ("Housing", True),
            ("Car", False),
            ("Utility", True),
        ]
        allowance_objs = {}
        for name, taxable in allowance_types:
            obj, _ = AllowanceType.objects.get_or_create(
                tenant=tenant,
                name=name,
                defaults={"is_taxable": taxable},
            )
            allowance_objs[name] = obj

        # 1. Seed Grades
        grades = [
            ("Executive Trainee", 1),
            ("Assistant Officer", 2),
            ("Officer", 3),
            ("Senior Officer", 4),
            ("Assistant Manager", 5),
            ("Deputy Manager", 6),
            ("Manager", 7),
            ("Senior Manager", 8),
            ("Assistant General Manager", 9),
            ("Deputy General Manager", 10),
            ("General Manager", 11),
            ("Executive Director", 12),
            ("Managing Director", 13),
        ]
        grade_objs = []
        for name, level in grades:
            g, _ = Grade.objects.get_or_create(
                tenant=tenant,
                name=name,
                level=level,
                defaults={"annual_leave_days": 20, "basic_salary": 100000 * level},
            )
            grade_objs.append(g)

        # Seed Grade Allowances for executives
        for grade in grade_objs:
            if grade.level in executive_allowances:
                for name, amount in executive_allowances[grade.level].items():
                    GradeAllowance.objects.get_or_create(
                        tenant=tenant,
                        grade=grade,
                        allowance_type=allowance_objs[name],
                        defaults={"amount": amount},
                    )

        # 2. Salary bands
        salary_bands = {
            1: (100000, 150000),
            2: (150000, 200000),
            3: (200000, 300000),
            4: (300000, 400000),
            5: (400000, 500000),
            6: (500000, 600000),
            7: (500000, 700000),
            8: (700000, 900000),
            9: (900000, 1100000),
            10: (1100000, 1300000),
            11: (1300000, 1500000),
            12: (1500000, 2000000),
            13: (2000000, 3000000),
        }

        # 3. Seed Employees
        employees = []
        for i in range(67,195):
            user, created = User.objects.get_or_create(
                email=f"employee{i}@example.com",
                defaults={"full_name": fake.name()},
            )
            if created:
                user.set_password("changeme123")
                user.save()

            grade_choice = random.choice(grade_objs)
            band_min, band_max = salary_bands[grade_choice.level]
            base_salary = random.randint(band_min, band_max)

            # Add allowances if executive grade
            extra_allowances = 0
            if grade_choice.level in executive_allowances:
                for amount in executive_allowances[grade_choice.level].values():
                    extra_allowances += amount

            final_base_pay = base_salary + extra_allowances

            emp = Employee.objects.create(
                tenant=tenant,
                user=user,
                employee_id=f"E{i:03}",
                employee_email=f"employee{i}@company.com",
                grade=grade_choice,
                grade_base_pay=grade_choice,
                above_grade_base_pay=extra_allowances,
                base_pay=final_base_pay,
                first_name=user.full_name.split()[0],
                last_name=user.full_name.split()[-1],
                date_of_birth=fake.date_of_birth(minimum_age=22, maximum_age=55),
                gender=random.choice(["M", "F"]),
                national_id_number=f"NID{i:03}",
            )
            employees.append(emp)

        # 4. Link Applications (assumes candidates already seeded)
        applications = Application.objects.filter(tenant=tenant)[:20]

        # 5. Create Interviews
        for app in applications:
            interview = Interview.objects.create(
                tenant=tenant,
                application=app,
                scheduled_at=fake.future_datetime(),
                setup_by=random.choice(employees),
            )
            interviewers = random.sample(employees, 2)
            for interviewer in interviewers:
                InterviewFeedback.objects.create(
                    tenant=tenant,
                    interview=interview,
                    interviewer=interviewer,
                    notes=fake.sentence(),
                    rating=random.randint(1, 5),
                    verdict=random.choice(["PASS", "FAIL", "KIV"]),
                )

        self.stdout.write(self.style.SUCCESS("Seeded Grades, Employees with salary bands + allowances, Applications, and Interviews"))