from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from org.models import Tenant, Grade
from org.models import PyramidGroup 

class Command(BaseCommand):
    help = "Seeds PyramidGroups and Grades for Tenant DMC with % incremental salaries."

    def handle(self, *args, **options):
        try:
            tenant = Tenant.objects.get(code="DMC")
        except Tenant.DoesNotExist:
            self.stderr.write("Tenant 'DMC' not found.")
            return

        # 1. Pyramid Groups
        pyramid_data = [
            ("Staff", 1, 15),
            ("Middle Management", 2, 21),
            ("Senior Management", 3, 26),
            ("Top Management", 4, 30),
        ]

        # 2. Grade Mapping (Level 15 = Highest)
        grade_list = [
            ("Chairman", 15, "Top Management"),
            ("Managing Director", 14, "Top Management"),
            ("Executive Director", 13, "Top Management"),
            ("General Manager", 12, "Senior Management"),
            ("Deputy General Manager", 11, "Senior Management"),
            ("Assistant General Manager", 10, "Senior Management"),
            ("Senior Manager", 9, "Middle Management"),
            ("Manager", 8, "Middle Management"),
            ("Deputy Manager", 7, "Middle Management"),
            ("Assistant Manager", 6, "Middle Management"),
            ("Senior Officer", 5, "Staff"),
            ("Officer", 4, "Staff"),
            ("Executive Trainee", 3, "Staff"),
            ("Intern", 2, "Staff"),
            ("Contract Staff", 1, "Staff"),
        ]

        base_salary = 150000
        percent_increase = 0.15  # 15%

        with transaction.atomic():
            self.stdout.write("Creating Pyramid Groups...")
            pyramid_objs = {}
            for name, level, leave in pyramid_data:
                pg, _ = PyramidGroup.objects.get_or_create(
                    tenant=tenant, name=name, level=level
                )
                pyramid_objs[name] = {"obj": pg, "leave": leave}

            self.stdout.write("Calculating Salaries with 15% Compound Growth...")
            
            # We sort grades by level ascending to calculate compound growth correctly
            sorted_grades = sorted(grade_list, key=lambda x: x[1])
            
            for name, level, pg_name in sorted_grades:
                pg_info = pyramid_objs[pg_name]
                
                # Formula: Base * (1 + r)^(level - 1)
                salary_raw = base_salary * ((1 + percent_increase) ** (level - 1))
                
                # Round to nearest 500 for professional payroll formatting
                salary_final = round(salary_raw / 500) * 500

                Grade.objects.update_or_create(
                    tenant=tenant,
                    level=level,
                    defaults={
                        "name": name,
                        "pyramid": pg_info["obj"],
                        "annual_leave_days": pg_info["leave"],
                        "basic_salary": Decimal(str(salary_final))
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded Grades for DMC with 15% increments."))