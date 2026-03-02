import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from org.models import Tenant, Grade
from employees.models import Employee
from development.models import (
    Skill, Competency, 
    Appraisal, SkillMatrix, GradeRequirement
)
from performance.models import AppraisalCycle,PerformanceIndicator,AppraisalRating

class Command(BaseCommand):
    help = "Seeds Skills, Gaps, and performs Bell Curve Normalization safely."

    def handle(self, *args, **options):
        tenant = Tenant.objects.get(code="DMC")
        employees = list(Employee.objects.filter(tenant=tenant))
        
        if not employees:
            self.stdout.write(self.style.ERROR("No employees found. Seed employees first."))
            return

        with transaction.atomic():
            self.stdout.write("Initializing Skills and Grade Requirements...")
            # 1. Seed Skills & Competencies
            skill_names = ["Python", "SQL", "Strategic Thinking", "Public Speaking", "Negotiation"]
            skills = [Skill.objects.get_or_create(tenant=tenant, name=s)[0] for s in skill_names]

            # 2. Set 'The Bar' (Grade Requirements)
            for grade in Grade.objects.filter(tenant=tenant):
                # Senior grades require Level 4, others Level 2
                req_lvl = 4 if grade.level > 10 else 2
                GradeRequirement.objects.get_or_create(
                    tenant=tenant, grade=grade, skill=skills[0],
                    defaults={'minimum_level': req_lvl}
                )

            # 3. Create 'The Reality' (Skill Matrix with Gaps)
            for emp in employees:
                for skill in skills:
                    SkillMatrix.objects.update_or_create(
                        tenant=tenant, employee=emp, skill=skill,
                        defaults={'level': random.randint(1, 5)}
                    )

            # 4. Appraisal Cycle Setup
            cycle, _ = AppraisalCycle.objects.get_or_create(
                tenant=tenant, name="FY 2025 Annual Review",
                defaults={'start_date': "2025-01-01", 'end_date': "2025-12-31", 'is_active': True}
            )

            # 5. Generate Indicators and Ratings
            self.stdout.write("Generating weighted indicators and scores...")
            appraisal_list = []
            for i, emp in enumerate(employees):
                # STEP 1: Create initially in DRAFT to bypass the high-performer comparison logic
                appraisal = Appraisal.objects.create(
                    tenant=tenant, employee=emp, cycle=cycle,
                    manager=emp.line_manager, status='DRAFT'
                )

                # Define 3 Indicators totaling 100%
                indicators = [
                    (f"Revenue Target - {emp.employee_id}", "KPI", 60),
                    (f"Leadership Excellence - {emp.employee_id}", "COMP", 20),
                    (f"Core Values - {emp.employee_id}", "BEH", 20)
                ]

                for title, cat, weight in indicators:
                    ind = PerformanceIndicator.objects.create(
                        tenant=tenant, employee=emp, cycle=cycle,
                        title=title, category=cat, weight=weight, target_value="100%"
                    )

                    # Bias scores for the Bell Curve
                    seed_rand = random.random()
                    if seed_rand < 0.15: manager_score = random.randint(1, 2) # Underperformers
                    elif seed_rand > 0.85: manager_score = 5 # Top talent
                    else: manager_score = random.randint(3, 4) # Average

                    # STEP 2: Create Rating. 
                    # Note: Your AppraisalRating.save() calls appraisal.calculate_score()
                    AppraisalRating.objects.create(
                        tenant=tenant, appraisal=appraisal, indicator=ind,
                        self_score=random.randint(3, 5),
                        manager_score=manager_score,
                        manager_comment="Seeded via development script."
                    )
                
                # STEP 3: Now that ratings are saved and calculate_score() has run, 
                # final_score is NO LONGER None. We can safely change status.
                if i < 50: target_status = 'DRAFT'
                elif i < 150: target_status = 'REVIEW'
                elif i < 300: target_status = 'leave_application'
                else: target_status = 'COMPLETED'

                appraisal.status = target_status
                appraisal.save() # This triggers your high-performer check safely
                appraisal_list.append(appraisal)

            # 6. Apply Normalization (The Bell Curve)
            self.stdout.write("Applying Bell Curve Normalization...")
            # Sort by final_score (handle None just in case)
            processed_apps = sorted(appraisal_list, key=lambda x: x.final_score or 0, reverse=True)
            total = len(processed_apps)

            top_10 = int(total * 0.10)
            bottom_20 = int(total * 0.80)

            for idx, app in enumerate(processed_apps):
                if idx < top_10:
                    app.normalized_grade = "A"
                elif idx < bottom_20:
                    app.normalized_grade = "B"
                else:
                    app.normalized_grade = "C"
                
                app.is_moderated = True
                app.save()

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded development data for {len(employees)} employees."))