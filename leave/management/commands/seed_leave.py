import random
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from leave.models import LeaveType, LeaveFrequency, LeaveBalance, LeaveRequest, PublicHoliday
from employees.models import Employee
from development.models import Appraisal
from org.models import Tenant
class Command(BaseCommand):
    help = "Seeds Leave system with Grade-based Annual Leave and 4-Month Maternity Leave."

    def handle(self, *args, **options):
        tenant = Tenant.objects.get(code="DMC")
        
        with transaction.atomic():
            # 1. Frequencies
            f_annual, _ = LeaveFrequency.objects.get_or_create(tenant=tenant, name="Annual", month_span=12)

            # 2. Leave Types
            lt_annual, _ = LeaveType.objects.get_or_create(
                tenant=tenant, name="Annual Leave",
                defaults={'base_entitlement': 20, 'frequency': f_annual}
            )
            
            lt_maternity, _ = LeaveType.objects.get_or_create(
                tenant=tenant, name="Maternity Leave",
                defaults={
                    'is_event_based': True,
                    'fixed_duration_value': 4,
                    'duration_unit': 'MONTHS',
                    'is_paid': True,
                    'requires_attachment': True
                }
            )

            # 3. Public Holidays (Used for Annual Leave duration but NOT Maternity)
            holidays = [("New Year", date(2026, 1, 1)), ("Workers Day", date(2026, 5, 1))]
            for name, d in holidays:
                PublicHoliday.objects.get_or_create(tenant=tenant, name=name, date=d)

            # 4. Process Employees
            employees = Employee.objects.filter(tenant=tenant)
            for i, emp in enumerate(employees):
                # ANNUAL LEAVE LOGIC
                grade_days = Decimal(getattr(emp.grade, 'annual_leave_days', 20))
                high_perf = Appraisal.objects.filter(employee=emp, normalized_grade='A').exists()
                total_annual = grade_days + (Decimal('2.0') if high_perf else 0)

                LeaveBalance.objects.get_or_create(
                    tenant=tenant, employee=emp, leave_type=lt_annual, year=2026,
                    defaults={'total_earned': total_annual}
                )

                # SEED HISTORIC REQUESTS
                if i % 15 == 0: # Randomly seed some maternity leaves
                    LeaveRequest.objects.create(
                        tenant=tenant, employee=emp, leave_type=lt_maternity,
                        start_date=date(2026, 2, 1), # End date auto-calculated to June 1
                        status="APPROVED", reason="Maternity Leave"
                    )

                if i % 5 == 0: # Seed some annual leave
                    lr = LeaveRequest.objects.create(
                        tenant=tenant, employee=emp, leave_type=lt_annual,
                        start_date=date(2026, 1, 10), end_date=date(2026, 1, 15),
                        status="APPROVED", reason="Family vacation"
                    )
                    lr.deduct_from_balance()

        self.stdout.write(self.style.SUCCESS("Leave seeding complete with Calendar-based Maternity logic."))