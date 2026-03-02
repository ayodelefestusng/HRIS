from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone
from employees.models import Employee
from org.models import Department, Unit,OrgUnit

class ShiftSchedule(models.Model):
    """
    Defines a scheduled work shift for a department/unit.
    Supports flexible day cycles (Mon–Sun, Mon–Fri, etc.).
    """

    name = models.CharField(max_length=100)
    unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, related_name="shifts", null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    # Store cycle as comma-separated days (Mon,Tue,Wed,Thu,Fri or Mon,Sun,...)

    days_of_week = models.CharField(max_length=50, help_text="Comma-separated days e.g. Mon,Tue,Wed")
    
    employees_required = models.PositiveIntegerField(
        default=1,
        help_text="Number of employees required per day for this shift"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.start_time}-{self.end_time})"
    
    def get_days(self):
        """Return list of days in this shift cycle."""
        return [day.strip() for day in self.days_of_week.split(",")]


class ShiftAssignment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="shift_assignments")
    shift = models.ForeignKey(ShiftSchedule, on_delete=models.CASCADE, related_name="assignments")
    date = models.DateField()

    class Meta:
        unique_together = ("employee", "shift", "date")

    def __str__(self):
        return f"{self.employee} - {self.shift.name} on {self.date}"

class AttendanceRecord(models.Model):
    """
    Daily attendance record for an employee.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField(default=timezone.now)
    shift = models.ForeignKey(ShiftSchedule, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ("PRESENT", "Present"),
            ("ABSENT", "Absent"),
            ("LATE", "Late"),
            ("EXCUSED", "Excused"),
        ],
        default="PRESENT"
    )
    clock_in = models.TimeField(null=True, blank=True)
    clock_out = models.TimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.status})"


class OvertimeRecord(models.Model):
    """
    Records overtime hours worked by an employee.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="overtime_records")
    date = models.DateField(default=timezone.now)
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_overtime")

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.hours} hrs)"


class ClockLog(models.Model):
    """
    Manual clock-in/clock-out log for employees.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="clock_logs")
    timestamp = models.DateTimeField(default=timezone.now)
    action = models.CharField(
        max_length=10,
        choices=[
            ("IN", "Clock In"),
            ("OUT", "Clock Out"),
        ]
    )
    source = models.CharField(max_length=20, default="MANUAL", help_text="Manual, Biometric, Web, Mobile")

    def __str__(self):
        return f"{self.employee} - {self.action} at {self.timestamp}"