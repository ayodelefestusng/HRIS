import random
from datetime import timedelta, date
from faker import Faker
from django.core.management.base import BaseCommand
from org.models import Tenant
from ats.models import Application, Interview, InterviewFeedback, Offer
from employees.models import Employee
from collections import defaultdict
from statistics import mean


fake = Faker()

class Command(BaseCommand):
    help = "Seed Interviews, Feedback, and Offers for Tenant 3Line (offers only for >=2 PASS verdicts, 70% chance, salary bands with ±15% wiggle room)"

    def handle(self, *args, **options):
        try:
            tenant = Tenant.objects.get(code="3LN")
        except Tenant.DoesNotExist:
            self.stdout.write(self.style.ERROR("Tenant not found"))
            return

        employees = list(Employee.objects.filter(tenant=tenant))
        applications = list(Application.objects.filter(tenant=tenant))

        if not employees or not applications:
            self.stdout.write(self.style.ERROR("No employees or applications found"))
            return

        # Salary bands (same as earlier seeding)
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

        # Executive allowances
        executive_allowances = {
            11: {"Housing": 200000, "Car": 150000, "Utility": 50000},
            12: {"Housing": 300000, "Car": 200000, "Utility": 75000},
            13: {"Housing": 500000, "Car": 300000, "Utility": 100000},
        }

        interview_count = 0
        feedback_count = 0
        offer_count = 0

        for app in applications:
            # 1. Create Interview
            interview = Interview.objects.create(
                tenant=tenant,
                application=app,
                scheduled_at=fake.future_datetime(end_date="+30d"),
                setup_by=random.choice(employees),
            )
            interview_count += 1

            # 2. Assign 2–3 interviewers and feedback
            interviewers = random.sample(employees, k=min(3, len(employees)))
            verdicts = []
            for interviewer in interviewers:
                verdict = random.choice(["PASS", "FAIL", "KIV"])
                InterviewFeedback.objects.create(
                    tenant=tenant,
                    interview=interview,
                    interviewer=interviewer,
                    notes=fake.paragraph(nb_sentences=2),
                    rating=random.randint(1, 5),
                    verdict=verdict,
                )
                feedback_count += 1
                verdicts.append(verdict)

            # 3. Offer logic: at least two PASS verdicts required
            if verdicts.count("PASS") >= 2:
                # 70% chance of generating an offer
                if random.random() < 0.7:
                    grade = app.candidate.preferred_location and getattr(app.job_posting, "grade", None)
                    # fallback: pick random grade if not linked
                    grade_level = random.randint(1, 13)

                    band_min, band_max = salary_bands[grade_level]
                    # ±15% wiggle room
                    wiggle_min = int(band_min * 0.85)
                    wiggle_max = int(band_max * 1.15)
                    negotiated_salary = random.randint(wiggle_min, wiggle_max)

                    # Add allowances for executives
                    if grade_level in executive_allowances:
                        negotiated_salary += sum(executive_allowances[grade_level].values())

                    # Start date ranges by grade level
                    if grade_level <= 5:  # Junior
                        start_date = date.today() + timedelta(weeks=random.randint(2, 4))
                    elif grade_level <= 10:  # Mid-level
                        start_date = date.today() + timedelta(weeks=random.randint(4, 8))
                    else:  # Executives
                        start_date = date.today() + timedelta(weeks=random.randint(8, 12))

                    status = random.choice(["PENDING", "ACCEPTED", "DECLINED"])

                    Offer.objects.create(
                        tenant=tenant,
                        application=app,
                        salary=negotiated_salary,
                        start_date=start_date,
                        status=status,
                    )
                    offer_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {interview_count} interviews, {feedback_count} feedback entries, and {offer_count} offers (only for >=2 PASS verdicts, 70% chance)"
            )
        )
        grade_summary = defaultdict(list)

        # Collect offers by grade
        for offer in Offer.objects.filter(tenant=tenant):
            # Some applications may not have grade linked directly, so fallback
            grade_level = getattr(offer.application.candidate, "grade", None)
            if grade_level:
                grade_summary[grade_level.level].append(float(offer.salary))

        # Print summary
        self.stdout.write(self.style.SUCCESS("\n--- Offer Summary by Grade ---"))
        for level in sorted(grade_summary.keys()):
            salaries = grade_summary[level]
            avg_salary = mean(salaries) if salaries else 0
            self.stdout.write(
                f"Grade {level}: {len(salaries)} offers, Avg Salary ₦{avg_salary:,.0f}"
            )
