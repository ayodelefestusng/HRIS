import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

# Replace 'your_app' with the actual name of your apps
from core.models import Tenant # Assuming Tenant is here
from employees.models import Employee, OrgUnit 

from attendance.models import (
    ShiftSchedule, AttendanceRecord, ClockLog, 
    ShiftAssignment, OvertimeRecord, AttendanceLog, OvertimePolicy
)

class Command(BaseCommand):
    help = "Seeds the database with sample attendance and overtime data"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding attendance data...")

        # 1. Setup Tenant and OrgUnit
        tenant = Tenant.objects.first()
        if not tenant:
            self.stdout.write(self.style.ERROR("No Tenant found. Please create one first."))
            return

        org_unit, _ = OrgUnit.objects.get_or_create(
            name="Operations", tenant=tenant
        )

        # 2. Create Shift Schedules
        morning_shift, _ = ShiftSchedule.objects.get_or_create(
            tenant=tenant,
            name="Morning Shift",
            defaults={
                "org_unit": org_unit,
                "start_time": time(8, 0),
                "end_time": time(17, 0),
                "late_grace_period": 15,
                "days_of_week": "Mon,Tue,Wed,Thu,Fri"
            }
        )

        # 3. Create Overtime Policy
        ot_policy, _ = OvertimePolicy.objects.get_or_create(
            tenant=tenant,
            name="Standard OT Policy",
            defaults={
                "standard_rate": Decimal("1.50"),
                "weekend_rate": Decimal("2.00"),
                "minimum_overtime_minutes": 60
            }
        )

        # 4. Get Employees
        employees = Employee.objects.filter(tenant=tenant)[:5]
        if not employees.exists():
            self.stdout.write(self.style.ERROR("No Employees found to assign attendance to."))
            return

        # 5. Generate Data for the last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        current_date = start_date

        while current_date <= end_date:
            is_weekend = current_date.weekday() >= 5
            
            for emp in employees:
                # Skip weekends for standard attendance, but maybe add OT
                if is_weekend:
                    if random.choice([True, False, False]): # 33% chance of weekend OT
                        OvertimeRecord.objects.create(
                            tenant=tenant,
                            employee=emp,
                            date=current_date,
                            hours=Decimal("4.00"),
                            reason="Weekend Support"
                        )
                    continue

                # A. Shift Assignment
                ShiftAssignment.objects.get_or_create(
                    tenant=tenant, employee=emp, shift=morning_shift, date=current_date
                )

                # B. Simulation of Clock In/Out times
                # Randomly make some people late (After 08:15)
                is_late_today = random.random() < 0.2
                if is_late_today:
                    actual_in = time(8, 20)
                    status = "LATE"
                else:
                    actual_in = time(7, 55)
                    status = "PRESENT"

                actual_out = time(17, 5)

                # C. Create AttendanceRecord (The Source of Truth)
                AttendanceRecord.objects.update_or_create(
                    employee=emp,
                    date=current_date,
                    tenant=tenant,
                    defaults={
                        "shift": morning_shift,
                        "status": status,
                        "clock_in": actual_in,
                        "clock_out": actual_out,
                        "total_hours": Decimal("9.00"),
                        "data_source": "DEVICE",
                        "is_verified": True
                    }
                )

                # D. Create raw ClockLogs (The "Raw" pings)
                # Clock In log
                in_ts = timezone.make_aware(datetime.combine(current_date, actual_in))
                ClockLog.objects.create(
                    tenant=tenant, employee=emp, timestamp=in_ts, action="IN", device_id="BIO-001"
                )
                
                # Clock Out log
                out_ts = timezone.make_aware(datetime.combine(current_date, actual_out))
                ClockLog.objects.create(
                    tenant=tenant, employee=emp, timestamp=out_ts, action="OUT", device_id="BIO-001"
                )

                # E. Create AttendanceLog (The mirrored context log)
                AttendanceLog.objects.update_or_create(
                    employee=emp,
                    date=current_date,
                    tenant=tenant,
                    defaults={
                        "check_in": in_ts,
                        "check_out": out_ts,
                        "shift_start_expected": morning_shift.start_time,
                        "shift_end_expected": morning_shift.end_time,
                        "status": "LATE" if is_late_today else "PRESENT"
                    }
                )

            current_date += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded 30 days of data for {employees.count()} employees."))