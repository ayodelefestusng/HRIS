import random
from datetime import datetime, time, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from django.core.management.base import BaseCommand, color_style

# Import your models here

from org.models import Tenant, OrgUnit
from employees.models import Employee
from attendance.models import (
    ShiftSchedule,
    AttendanceRecord,
    ClockLog,
    ShiftAssignment,
    OvertimeRecord,
    AttendanceLog,
    OvertimePolicy,
)
from django.db import transaction
from leave.models import LeaveRequest, LeaveType, LeaveFrequency

fake = Faker()


class Command(BaseCommand):
    help = "Seeds the database with sample attendance and shift data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=14, help="Number of days to seed"
        )
        parser.add_argument(
            "--employees", type=int, default=5, help="Number of employees to seed"
        )
        # FIX: Added the missing cleanup argument
        parser.add_argument(
            "--cleanup",
            action="store_true",
            help="Wipe existing attendance and leave data before seeding",
        )

    def cleanup_data(self):
        """Deletes existing transactional data to prevent duplicates."""
        self.stdout.write(self.style.WARNING("Cleaning up existing sample data..."))

        # Order of deletion is important for Foreign Key constraints
        ClockLog.objects.all().delete()
        AttendanceRecord.objects.all().delete()
        AttendanceLog.objects.all().delete()
        OvertimeRecord.objects.all().delete()
        ShiftAssignment.objects.all().delete()
        # # LeaveRequest.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Cleanup complete."))

    # @transaction.atomic
    def handle(self, *args, **options):
        # 1. Check for cleanup flag
        if options.get("cleanup"):
            self.cleanup_data()

        days_to_seed = options["days"]
        num_employees = options["employees"]

        self.stdout.write(self.style.SUCCESS("Starting seed..."))

        # 1. Get or Create a Tenant & OrgUnit (Placeholders)
        # Note: Adjust these based on your actual Tenant/OrgUnit model fields
        tenant, _ = Tenant.objects.get_or_create(name="DMC")

        # 2. Randomly use existing OrgUnit
        existing_orgs = list(OrgUnit.objects.filter(tenant=tenant))
        if not existing_orgs:
            self.stdout.write(
                self.style.WARNING(
                    "No OrgUnits found, creating a default 'Main Office'."
                )
            )
            org_unit = OrgUnit.objects.create(name="Main Office", tenant=tenant)
        else:
            org_unit = random.choice(existing_orgs)
            self.stdout.write(f"Using random OrgUnit: {org_unit.name}")

        # 1. Setup Leave Infrastructure with your LeaveFrequency model
        freq, _ = LeaveFrequency.objects.get_or_create(
            tenant=tenant, name="Annual", defaults={"month_span": 12}
        )

        sick_type, _ = LeaveType.objects.get_or_create(
            tenant=tenant,
            name="SICK",
            defaults={"is_paid": True, "base_entitlement": 10, "frequency": freq},
        )
        vacation_type, _ = LeaveType.objects.get_or_create(
            tenant=tenant,
            name="VACATION",
            defaults={"is_paid": True, "base_entitlement": 20, "frequency": freq},
        )

        # 2. Setup Shifts
        morning_shift, _ = ShiftSchedule.objects.update_or_create(
            tenant=tenant,
            name="Morning",
            defaults={
                "org_unit": org_unit,
                "start_time": time(8, 0),
                "end_time": time(17, 0),
                "late_grace_period": 15,
            },
        )

        # 2. Create Overtime Policy
        ot_policy, _ = OvertimePolicy.objects.get_or_create(
            tenant=tenant,
            name="Standard OT Policy",
            defaults={
                "standard_rate": 1.5,
                "weekend_rate": 2.0,
                "minimum_overtime_minutes": 60,
            },
        )

        # 1. Setup Shifts (Rotating & Night)
        morning_shift, _ = ShiftSchedule.objects.update_or_create(
            tenant=tenant,
            name="Morning",
            defaults={
                "org_unit": org_unit,
                "start_time": time(8, 0),
                "end_time": time(17, 0),
                "late_grace_period": 15,
            },
        )
        night_shift, _ = ShiftSchedule.objects.update_or_create(
            tenant=tenant,
            name="Night Shift",
            defaults={
                "org_unit": org_unit,
                "start_time": time(22, 0),
                "end_time": time(6, 0),
                "late_grace_period": 15,
            },
        )
        # 3. Employee Allocation (95-100% logic)
        all_employees = list(Employee.objects.filter(tenant=tenant))
        assigned_count = int(len(all_employees) * random.uniform(0.95, 1.0))
        assigned_staff = all_employees[:assigned_count]
        today = timezone.now().date()
        current_date = today - timedelta(days=150)
        rejection_reasons = [
            "Operational requirements - insufficient cover",
            "Exceeded annual leave entitlement",
            "Overlapping requests from senior team members",
            "Emergency project deadline",
        ]
        # --- Scenario: LEAVE REQUESTS (Including Rejections) ---
        leave_taken_today = (
            False  # Track if we already handled this day via leave logic
        )
        if not all_employees:
            self.stdout.write(
                self.style.WARNING("No employees found. Please seed employees first.")
            )
            return

        # 4. 5-Month Time Range
        # 3. Time Range: 5 Months

        self.stdout.write(f"Generating data for {len(assigned_staff)} staff members...")

        while current_date <= today:
            self.stdout.write(f"Seeding date: {current_date}")

            # Shift Rotation Logic: Change shift type every Monday
            # Shift Rotation Logic (Weekly)
            week_number = current_date.isocalendar()[1]
            active_shift = morning_shift if week_number % 2 == 0 else night_shift

            for emp in assigned_staff:
                leave_taken_today = False
                # Randomly assign a shift for the day
                # 1. Determine if the employee is on leave today (10% chance)

                is_monday = current_date.weekday() == 0
                leave_chance = 0.15 if is_monday else 0.05
                is_rejected = random.random() < 0.20  # 20% of requests get rejected
                leave_status = "REJECTED" if is_rejected else "APPROVED"

                if random.random() < leave_chance:
                    leave_app = LeaveRequest.objects.create(
                        tenant=tenant,
                        employee=emp,
                        start_date=current_date,
                        end_date=current_date,
                        status=leave_status,
                        leave_type=random.choice([sick_type, vacation_type]),
                        # Set rejection_reason if applicable (assuming field name)
                        rejection_reason=(
                            random.choice(rejection_reasons) if is_rejected else ""
                        ),
                    )
                    if leave_status == "APPROVED":
                        AttendanceRecord.objects.create(
                            tenant=tenant,
                            employee=emp,
                            date=current_date,
                            status="EXCUSED",
                        )
                        # 4. FIX: Create AttendanceLog with EXPECTED SHIFT TIMES
                        AttendanceLog.objects.update_or_create(
                            tenant=tenant,
                            employee=emp,
                            date=current_date,
                            defaults={
                                "status": "EXCUSED",
                                "is_excused": True,
                                "excusal_reason": f"Approved Leave: {leave_app.leave_type.name}",
                                "shift_start_expected": active_shift.start_time,
                                "shift_end_expected": active_shift.end_time,
                            },
                        )
                        continue  # Skip to next employee, they are legally away

                    else:
                        # If REJECTED, and they don't show up, they are ABSENT
                        if (
                            random.random() < 0.5
                        ):  # 50% chance they stayed home anyway (AWOL)
                            AttendanceRecord.objects.create(
                                tenant=tenant,
                                employee=emp,
                                date=current_date,
                                status="ABSENT",
                                data_source="SYSTEM",
                                remarks=f"AWOL: Leave request {leave_app.id} was rejected.",
                            )
                            continue
                    # --- SCENARIO 2: Weekend/Holiday Off ---
                # --- REGULAR ATTENDANCE LOGIC (For those not on approved leave) ---
                if current_date.weekday() >= 5:
                    continue

                # --- SCENARIO 3: Generate Clock Data ---
                # Randomize behavior
                # --- Scenario: Attendance Clocking ---
                is_late = random.random() < (0.18 if is_monday else 0.05)
                arrival_offset = (
                    random.randint(16, 45) if is_late else random.randint(-15, 10)
                )

                in_dt = datetime.combine(
                    current_date, active_shift.start_time
                ) + timedelta(minutes=arrival_offset)

                # Handling Night Shift Cross-over
                # Handling Cross-over (Night Shift)
                if active_shift.end_time < active_shift.start_time:
                    out_dt = datetime.combine(
                        current_date + timedelta(days=1), active_shift.end_time
                    )
                else:
                    out_dt = datetime.combine(current_date, active_shift.end_time)

                # out_dt += timedelta(minutes=random.randint(-30, 90)) # Random early exit/OT
                # Today Logic: Leave some people "Currently In"
                is_currently_in = current_date == today and random.random() < 0.4
                final_out_dt = (
                    out_dt + timedelta(minutes=random.randint(-10, 120))
                    if not is_currently_in
                    else None
                )

                # --- REGULAR ATTENDANCE LOGIC ---
                # Only proceed if they didn't have an approved leave record created above
                if not leave_taken_today and current_date.weekday() < 5:
                    is_late = random.random() < (
                        0.18 if current_date.weekday() == 0 else 0.05
                    )
                    # ... (in_dt and final_out_dt calculation logic here) ...

                    AttendanceLog.objects.update_or_create(
                        tenant=tenant,
                        employee=emp,
                        date=current_date,
                        defaults={
                            "check_in": timezone.make_aware(in_dt),
                            "check_out": (
                                timezone.make_aware(final_out_dt)
                                if final_out_dt
                                else None
                            ),
                            "shift_start_expected": active_shift.start_time,
                            "shift_end_expected": active_shift.end_time,
                            "status": "LATE" if is_late else "PRESENT",
                            "gps_location": (
                                "6.5244, 3.3792"
                                if random.random() > 0.05
                                else "9.9999, 1.1111"
                            ),
                            "ip_address": "192.168.1." + str(random.randint(2, 254)),
                        },
                    )

                # 5. Attendance Record
                hours_worked = (
                    (final_out_dt - in_dt).total_seconds() / 3600 if final_out_dt else 0
                )
                AttendanceRecord.objects.create(
                    tenant=tenant,
                    employee=emp,
                    date=current_date,
                    shift=active_shift,
                    clock_in=in_dt.time(),
                    clock_out=final_out_dt.time() if final_out_dt else None,
                    status="LATE" if is_late else "PRESENT",
                    total_hours=round(hours_worked, 2),
                    is_under_hours=hours_worked < 7.5 if final_out_dt else False,
                    is_verified=random.random() > 0.15,  # 15% Pending Verification
                )

                # 6. Overtime (Pending logic)
                if hours_worked > 9.5:
                    OvertimeRecord.objects.create(
                        tenant=tenant,
                        employee=emp,
                        date=current_date,
                        hours=round(hours_worked - 9, 2),
                        status="PENDING" if random.random() < 0.3 else "APPROVED",
                    )

            # Increment the date to prevent infinite loop
            current_date += timedelta(days=1)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {days_to_seed} days of data.")
        )
        self.show_visual_dashboard(tenant)

    def show_visual_dashboard(self, tenant):
        """Terminal-based Visual Dashboard View"""
        self.stdout.write("\n" + "═" * 50)
        self.stdout.write(
            " 📈  HR ANALYTICS EXECUTIVE SUMMARY (5 MONTHS) ".center(50, "═")
        )
        self.stdout.write("═" * 50)

        # Aggregations
        total = AttendanceRecord.objects.filter(tenant=tenant).count()
        late = AttendanceRecord.objects.filter(tenant=tenant, status="LATE").count()
        under = AttendanceRecord.objects.filter(
            tenant=tenant, is_under_hours=True
        ).count()
        pending = AttendanceRecord.objects.filter(
            tenant=tenant, is_verified=False
        ).count()
        live_in = AttendanceRecord.objects.filter(
            date=timezone.now().date(), clock_out__isnull=True
        ).count()

        # Visual Indicators
        self.stdout.write(f"▶ TOTAL RECORDS PROCESSED   : {total}")
        self.stdout.write(
            f"▶ CURRENTLY CLOCKED IN      : {self.style.HTTP_INFO(str(live_in))} staff"
        )
        self.stdout.write(
            f"▶ CHRONIC LATENESS RATE     : {round((late/total)*100, 1)}% ⚠️"
        )
        self.stdout.write(f"▶ LABOR LEAKAGE (Under Hrs) : {under} instances")
        self.stdout.write(f"▶ MANAGER BACKLOG (Pending) : {pending} records")
        self.stdout.write("═" * 50 + "\n")


# python manage.py seed_attendance --cleanup
