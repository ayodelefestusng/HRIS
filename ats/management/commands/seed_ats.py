import random
import uuid
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
import io

from org.models import Tenant, OrgUnit, Location, Skill, Competency
from employees.models import Employee
from ats.models import (
    JobPosting, Candidate, Application, Interview, 
    InterviewFeedback, Offer, OnboardingTemplate, 
    OnboardingPlan, OnboardingTask
)

class Command(BaseCommand):
    help = "Seeds 500 Candidates and 20 Job Postings with full recruitment history."

    def handle(self, *args, **options):
        tenant = Tenant.objects.get(code="DMC")
        exec_pool = list(Employee.objects.filter(tenant=tenant, grade__level__gte=12))
        locations = list(Location.objects.filter(tenant=tenant))
        units = list(OrgUnit.objects.all())

        def gen_pdf(name, doc_type="Resume"):
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer)
            p.drawString(100, 750, f"{doc_type}: {name}")
            p.drawString(100, 730, f"Generated for {tenant.name} ATS Seed.")
            p.showPage()
            p.save()
            return ContentFile(buffer.getvalue(), f"{name.replace(' ', '_')}_{doc_type}.pdf")

        with transaction.atomic():
            self.stdout.write("Seeding Jobs and Candidates...")

            # 1. Create Job Postings
            jobs = []
            job_titles = ["Senior Developer", "HR Business Partner", "Risk Analyst", "Accountant", "Sales Manager", "Branch Ops Lead"]
            for i in range(20):
                job = JobPosting.objects.create(
                    tenant=tenant,
                    title=random.choice(job_titles),
                    unit=random.choice(units),
                    description="Standard job description for simulated testing.",
                    requirements="Minimum 5 years experience and relevant certifications.",
                    status="OPEN",
                    posted_at=timezone.now() - timedelta(days=30)
                )
                job.locations.add(random.choice(locations))
                jobs.append(job)

            # 2. Create Candidates and Applications
            first_names = ["Chidi", "Funke", "Ibrahim", "Ngozi", "Tunde", "Amina", "Emeka"]
            last_names = ["Okonkwo", "Balogun", "Abubakar", "Adeyemi", "Eze", "Bello"]

            self.stdout.write("Generating 500 candidates and history...")
            for i in range(500):
                full_name = f"{random.choice(first_names)} {random.choice(last_names)} {uuid.uuid4().hex[:4]}"
                email = f"candidate_{i}_{uuid.uuid4().hex[:4]}@example.com"
                
                candidate = Candidate.objects.create(
                    tenant=tenant,
                    full_name=full_name,
                    email=email,
                    phone=f"080{random.randint(10000000, 99999999)}",
                    preferred_location=random.choice(locations),
                    resume=gen_pdf(full_name, "Resume")
                )

                # Assign candidate to a random job
                job = random.choice(jobs)
                status_roll = random.random()

                if status_roll < 0.60:
                    status = "APPLIED"
                elif status_roll < 0.85:
                    status = "INTERVIEW"
                elif status_roll < 0.92:
                    status = "OFFER"
                elif status_roll < 0.97:
                    status = "HIRED"
                else:
                    status = "REJECTED"

                app = Application.objects.create(
                    tenant=tenant,
                    candidate=candidate,
                    job_posting=job,
                    status=status
                )

                # 3. Handle Interviews
                if status in ["INTERVIEW", "OFFER", "HIRED"]:
                    interview = Interview.objects.create(
                        tenant=tenant,
                        application=app,
                        scheduled_at=timezone.now() - timedelta(days=5),
                        setup_by=random.choice(exec_pool)
                    )
                    # Add Feedback
                    InterviewFeedback.objects.create(
                        tenant=tenant,
                        interview=interview,
                        interviewer=random.choice(exec_pool),
                        verdict="PASS",
                        rating=random.randint(3, 5),
                        notes="Candidate showed great technical depth."
                    )

                # 4. Handle Offers & Onboarding
                if status in ["OFFER", "HIRED"]:
                    Offer.objects.create(
                        tenant=tenant,
                        application=app,
                        salary=random.randint(250000, 800000),
                        start_date=timezone.now().date() + timedelta(days=14),
                        status="ACCEPTED" if status == "HIRED" else "PENDING",
                        acceptance_letter=gen_pdf(full_name, "Offer_Acceptance") if status == "HIRED" else None
                    )

                if status == "HIRED":
                    plan = OnboardingPlan.objects.create(
                        tenant=tenant,
                        application=app,
                        start_date=timezone.now().date(),
                        status="leave_application", # Per requirement
                        mentor=random.choice(exec_pool)
                    )
                    # Add Onboarding Tasks
                    for task_title in ["IT Setup", "Submit Credentials", "Culture Training"]:
                        OnboardingTask.objects.create(
                            tenant=tenant,
                            plan=plan,
                            title=task_title,
                            due_date=timezone.now().date() + timedelta(days=7)
                        )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded ATS with 500 candidates across 20 jobs."))