from django.db import models
from django.utils import timezone
from employees.models import Employee


class LeaveFrequency(models.Model):
    """
    Defines how often a leave type can be taken.
    Examples: Annual, Monthly, Quarterly, Bi-Monthly, Bi-Annual.
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    # Optional: number of months span for this frequency
    month_span = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Span in months (e.g. 1=Monthly, 3=Quarterly, 6=Bi-Annual)"
    )

    def __str__(self):
        return self.name
class LeaveType(models.Model):
    """
    Defines a type of leave (e.g., Annual Leave, Sick Leave).
    Linked to a frequency rule.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_paid = models.BooleanField(default=True)
    annual_allocation_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # ForeignKey to frequency
    frequency = models.ForeignKey(
        LeaveFrequency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leave_types"
    )

    block_leave_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Minimum consecutive days required (e.g. 10 for block annual leave)"
    )

    def __str__(self):
        return self.name
    
    
class LeaveRequest(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")],
        default="PENDING"
    )

    def clean(self):
        from django.core.exceptions import ValidationError

        days_requested = (self.end_date - self.start_date).days + 1

        # Block leave rule
        if self.leave_type.block_leave_days and days_requested < self.leave_type.block_leave_days:
            raise ValidationError(
                f"{self.leave_type.name} requires at least {self.leave_type.block_leave_days} consecutive days."
            )

        # Frequency rules via LeaveFrequency
        frequency = self.leave_type.frequency
        if frequency:
            # If month_span is defined, enforce that the request stays within that span
            if frequency.month_span:
                start_month = self.start_date.month
                end_month = self.end_date.month
                month_diff = abs(end_month - start_month)

                if month_diff >= frequency.month_span:
                    raise ValidationError(
                        f"{self.leave_type.name} ({frequency.name}) leave must be taken within {frequency.month_span} month(s)."
                    )

            # Example: Annual frequency could mean only once per year
            if frequency.name.upper() == "ANNUAL":
                if self.start_date.year != self.end_date.year:
                    raise ValidationError("Annual leave must be within the same calendar year.")
                

class LeaveBalance(models.Model):
    """
    Tracks an employee's leave balance for a specific leave type and year.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField()
    balance_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        unique_together = ("employee", "leave_type", "year")

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.year})"

                
class PublicHoliday(models.Model):
    """
    Represents a public holiday that should be excluded from working day calculations.
    """
    name = models.CharField(max_length=150)
    date = models.DateField(unique=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.name} ({self.date})"