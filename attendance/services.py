# attendance/services.py
from datetime import datetime, combine
from .models import AttendanceRecord, ClockLog, ShiftAssignment
from leave.models import LeaveRequest



class AttendanceService:
    def __init__(self, tenant):
        self.tenant = tenant

    def process_day_for_employee(self, employee, target_date):
        # 1. Check for Approved Leave first (The "Override")
        # This prevents marking someone as 'ABSENT' when they are on 'APPROVED' leave
        leave_status = self.get_leave_status(employee, target_date)
        
        # 2. Get Raw Logs
        logs = ClockLog.objects.filter(
            employee=employee, 
            timestamp__date=target_date, 
            tenant=self.tenant
        ).order_by('timestamp')

        # 3. Get Assigned Shift
        assignment = ShiftAssignment.objects.filter(
            employee=employee, date=target_date, tenant=self.tenant
        ).first()
        shift = assignment.shift if assignment else None

        # 4. Determine Initial Status
        first_in = logs.filter(action="IN").first()
        last_out = logs.filter(action="OUT").last()
        
        status = "ABSENT"
        if leave_status:
            status = leave_status # EXCUSED or UNPAID_LEAVE
        elif logs.exists():
            status = "PRESENT"
            if shift and first_in:
                # Add grace period logic here (e.g., 15 mins)
                if first_in.timestamp.time() > shift.start_time:
                    status = "LATE"
        else:
            # If no logs and no leave, check if they were even supposed to work
            if not assignment:
                return # It's their day off; no record needed

        # 5. Final Write
        AttendanceRecord.objects.update_or_create(
            employee=employee,
            date=target_date,
            tenant=self.tenant,
            defaults={
                'clock_in': first_in.timestamp.time() if first_in else None,
                'clock_out': last_out.timestamp.time() if last_out else None,
                'status': status,
                'shift': shift
            }
        )

    def get_leave_status(self, employee, date):
        """Helper to determine if a date is covered by an approved leave."""
        # Note: We import LeaveRequest inside to avoid circular imports if necessary
        from leave.models import LeaveRequest 
        
        leave = LeaveRequest.objects.filter(
            employee=employee,
            start_date__lte=date,
            end_date__gte=date,
            status="APPROVED",
            tenant=self.tenant
        ).first()
        
        if leave:
            return "EXCUSED" if leave.leave_type.is_paid else "UNPAID_LEAVE"
        return None