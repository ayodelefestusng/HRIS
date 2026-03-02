import os
import random
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import transaction
from reportlab.pdfgen import canvas
from io import BytesIO

from org.models import Tenant, Grade
from employees.models import Employee, EmployeeDocument
from employees.models import CompanyPolicy, PolicyAcknowledgement # Adjust path as needed

class Command(BaseCommand):
    help = "Seeds policies, PDFs, acknowledgements, and adjusts payroll for 57 employees."

    def handle(self, *args, **options):
        tenant = Tenant.objects.get(code="DMC")
        employees = list(Employee.objects.filter(tenant=tenant))

        with transaction.atomic():
            # 1. Create Placeholder PDF Function
            def generate_pdf_content(title):
                buffer = BytesIO()
                p = canvas.Canvas(buffer)
                p.drawString(100, 750, f"DMC Official Policy: {title}")
                p.drawString(100, 730, f"Version: 1.0 | Effective Date: {timezone.now().date()}")
                p.showPage()
                p.save()
                return ContentFile(buffer.getvalue(), name=f"{title.replace(' ', '_')}.pdf")

            # 2. Seed Company Policies
            policy_titles = [
                "Employee Handbook", "IT Security Policy", 
                "Remote Work Policy", "Code of Conduct", "Anti-Harassment Policy"
            ]
            policies = []
            self.stdout.write("Generating Policy PDFs...")
            for title in policy_titles:
                policy, _ = CompanyPolicy.objects.get_or_create(
                    tenant=tenant, title=title, version="1.0",
                    defaults={
                        "file": generate_pdf_content(title),
                        "requires_signature": True
                    }
                )
                policies.append(policy)

            # 3. Signature Backlog (257 Employees)
            # 3. Signature Backlog (Adjusted for actual population)
            num_to_sign = min(len(employees), 257) # Pick 257 or the max available
            self.stdout.write(f"Creating signatures for {num_to_sign} employees across grades...")
            
            if num_to_sign > 0:
                signing_pool = random.sample(employees, num_to_sign)
                for emp in signing_pool:
                    # Sign 1-3 random policies for each selected employee
                    for policy in random.sample(policies, random.randint(1, 3)):
                        mock_hash = hashlib.sha256(f"{emp.employee_id}-{timezone.now()}".encode()).hexdigest()
                        PolicyAcknowledgement.objects.get_or_create(
                            tenant=tenant, employee=emp, policy=policy,
                            defaults={
                                "digital_signature": mock_hash, 
                                "comments": "Automated migration signature."
                            }
                        )
            else:
                self.stderr.write("No employees found to sign policies. Skipping backlog.")
            # 4. Employee Documents (Contract & NDA for every employee)
            self.stdout.write("Uploading Contracts and NDAs for all staff...")
            for emp in employees:
                for doc_type, name in [("CNTR", "Employment Contract"), ("NDA", "Non-Disclosure Agreement")]:
                    expiry = timezone.now().date() + timedelta(days=random.randint(365, 1095))
                    EmployeeDocument.objects.get_or_create(
                        tenant=tenant, employee=emp, name=name, doc_type=doc_type,
                        defaults={"file": generate_pdf_content(name), "expires_at": expiry}
                    )

            # 5. Financial Adjustment: Above Grade Base Pay (57 Employees)
            self.stdout.write("Adjusting payroll for 57 employees (7-18% boost)...")
            # Selecting 57 employees between ET (Level 3) and ED (Level 13)
            eligible_staff = [e for e in employees if 3 <= e.grade.level <= 13]
            bonus_pool = random.sample(eligible_staff, 57)

            for emp in bonus_pool:
                grade_basic = float(emp.grade.basic_salary)
                percentage = random.uniform(0.07, 0.18)
                bonus_amount = round(grade_basic * percentage, -2) # Round to nearest 100
                
                emp.above_grade_base_pay = int(bonus_amount)
                # save() will trigger full_clean and calculate base_pay automatically
                emp.save()

        self.stdout.write(self.style.SUCCESS("Compliance and Financial seeds completed successfully!"))