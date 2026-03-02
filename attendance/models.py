import logging

from django.db import models
from django.utils import timezone

from employees.models import Employee
from org.models import OrgUnit, TenantModel
from datetime import datetime, timedelta
from org.views import log_with_context  
logger = logging.getLogger(__name__)


class ShiftSchedule(TenantModel):
    """
    World-class: Added Grace Periods and Overtime thresholds.
    """

    name = models.CharField(max_length=100)
    org_unit = models.ForeignKey(
        OrgUnit, on_delete=models.CASCADE, related_name="shifts"
    )
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Grace periods (in minutes)
    late_grace_period = models.PositiveIntegerField(
        default=15, help_text="Minutes before marked as Late"
    )
    early_exit_limit = models.PositiveIntegerField(
        default=15, help_text="Minutes allowed for early clock-out"
    )

    # Days of week as a bitmask or JSON is better, but keeping your comma-sep for now
    # days_of_week = models.CharField(max_length=50, help_text="Mon,Tue,Wed,Thu,Fri")
    days_of_week = models.JSONField(default=list,null=True, blank=True, help_text="Mon,Tue,Wed,Thu,Fri")
    # days_of_week = models.JSONField(default=list)
    
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("tenant", "name")

    def __str__(self):
        return f"{self.name} ({self.start_time}-{self.end_time})"


class AttendanceRecord(TenantModel):
    """
    The 'Source of Truth' for Payroll.
    """

    WORK_STATUS_CHOICES = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("LATE", "Late"),
        ("HALFDAY", "Half Day"),
        ("EXCUSED", "Excused"),
    ]
    
    STATUS_CHOICES =[
        ("pending", "Pending"), 
        ("rejected_for_amendment", "Rejected for Amendment"), 
        ("approved", "Approved"), 
        ("rejected", "Rejected")]
    SOURCE_CHOICES = [
        ("AUTO", "System Generated"),
        ("MANUAL", "Manual Entry"),
        ("DEVICE", "Biometric Sync"),
    ]
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField()
    shift = models.ForeignKey(ShiftSchedule, on_delete=models.SET_NULL, null=True)

    work_status = models.CharField(max_length=50, choices=WORK_STATUS_CHOICES, default="ABSENT")
    clock_in = models.TimeField(null=True, blank=True)
    clock_out = models.TimeField(null=True, blank=True)

    total_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_verified = models.BooleanField(default=False, help_text="Verified by Supervisor")
    data_source = models.CharField(
        max_length=10, choices=SOURCE_CHOICES, default="AUTO"
    )

    is_late = models.BooleanField(default=False)
    is_under_hours = models.BooleanField(default=False)
    remarks = models.TextField(blank=True) 
    
    
    is_approval_required = models.BooleanField(default=True)
    approval_status = models.CharField(
        max_length=50, 
        choices=STATUS_CHOICES,
        default='pending'
    ) 
    
    class Meta:
        unique_together = ("employee", "date", "tenant")
        indexes = [
            models.Index(fields=["employee", "date", "tenant"]),    
            models.Index(fields=["work_status", "date", "tenant"]),
        ]

    # def save(self, *args, **kwargs):
    #     # Logic to auto-set is_late before saving
    #     if self.clock_in and self.shift:
    #         if self.clock_in > self.shift.start_time:
    #             self.is_late = True
    #     super().save(*args, **kwargs)
    def save(self, *args, **kwargs):
        # 1. Approval Bypass Logic
        # Rule: Depth < 2 OR Pyramid Level > 10 bypasses approval
        emp = self.employee
        # Fetch depth from the primary org unit role
        primary_role = emp.roles.first()
        depth = primary_role.org_unit.depth if primary_role else 99
        pyramid_level = emp.grade.pyramid.level if emp.grade and emp.grade.pyramid else 0

        if depth < 2 or pyramid_level > 10:
            self.is_approval_required = False
            self.approval_status = 'approved'
            
        # 2. Logic for total hours & status
        if self.clock_in and self.clock_out:
            # Handle Night Shift crossover
            start = datetime.combine(self.date, self.clock_in)
            end = datetime.combine(self.date, self.clock_out)
            if end < start: # Crossover detected
                end += timedelta(days=1)
            
            diff = end - start
            self.total_hours = diff.total_seconds() / 3600

        super().save(*args, **kwargs)

    def apply_workflow_changes(self, actor):
        """
        Finalizes the attendance record approval.
        """
        self.approval_status = 'approved'
        self.is_verified = True
        self.save()
        log_with_context(logging.INFO, f"Attendance {self.id} approved via workflow.", actor.user)
        
    def __str__(self):
        return f"{self.employee} - {self.date} ({self.approval_status})"


class ClockLog(TenantModel):
    """
    Raw data from Web, Mobile (GPS), or Biometric devices.
    """

    ACTION_CHOICES = [("IN", "Clock In"), ("OUT", "Clock Out")]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="clock_logs"
    )
    timestamp = models.DateTimeField(default=timezone.now)
    action = models.CharField(max_length=3, choices=ACTION_CHOICES)

    class Meta:
        indexes = [
            models.Index(fields=["employee", "timestamp", "tenant"]),
        ]

    # Geofencing/Audit Data
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.employee.employee_id} - {self.action} @ {self.timestamp}"


class ShiftAssignment(TenantModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="shift_assignments"
    )
    shift = models.ForeignKey(
        ShiftSchedule, on_delete=models.CASCADE, related_name="assignments"
    )
    date = models.DateField()

    class Meta:
        unique_together = ("employee", "shift", "date")

    def __str__(self):
        return f"{self.employee} - {self.shift.name} on {self.date}"


class AttendanceLog(TenantModel):
    """
    Tracks daily clock-in/out data with geo-fencing and shift awareness.
    """

    STATUS_CHOICES = [
        ("PRESENT", "Present"),
        ("LATE", "Late"),
        ("ABSENT", "Absent"),
        ("EXCUSED", "Excused/Leave"),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="attendance_logs"
    )
    date = models.DateField(default=timezone.now)

    # Timing
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)

    # Context (Snapshots of shift requirements at time of clock-in)
    shift_start_expected = models.TimeField()
    shift_end_expected = models.TimeField()

    # Metadata for verification
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ABSENT")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    gps_location = models.CharField(
        max_length=100, null=True, blank=True, help_text="Lat, Long"
    )

    # Managerial overrides
    is_excused = models.BooleanField(default=False)
    excusal_reason = models.TextField(blank=True, null=True)
    verified_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        related_name="verified_logs",
    )

    class Meta:
        unique_together = ("employee", "date")
        ordering = ["-date", "employee"]

    def __str__(self):
        return f"{self.employee.first_name} {self.employee.last_name} - {self.date} ({self.status})"



class OvertimeRecord(TenantModel):
    """
    Records overtime hours worked by an employee.
    """
    STATUS_CHOICES =[
    ("pending", "Pending"), 
    ("rejected_for_amendment", "Rejected for Amendment"), 
    ("approved", "Approved"), 
    ("rejected", "Rejected")]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="overtime_records"
    )
    date = models.DateField(default=timezone.now)
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_overtime",
    )
    approval_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Approval status of the overtime request",
    )

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.hours} hrs)"


class OvertimePolicy(TenantModel):
    """
    Defines how OT is calculated for the tenant.
    """

    name = models.CharField(max_length=100)
    # Multipliers
    standard_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.5,
        help_text="Multiplier for normal work days",
    )
    weekend_rate = models.DecimalField(
        max_digits=4, decimal_places=2, default=2.0, help_text="Multiplier for Sat/Sun"
    )
    holiday_rate = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=2.5,
        help_text="Multiplier for Public Holidays",
    )

    # Thresholds
    minimum_overtime_minutes = models.PositiveIntegerField(
        default=60, help_text="Minimum minutes to qualify as OT"
    )
    requires_pre_approval = models.BooleanField(default=True)

    class Meta:
        unique_together = ("tenant", "name")
