from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone
from employees.models import Employee
#

class Warning(models.Model):
    """
    Records a formal warning issued to an employee.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="warnings")
    issued_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="warnings_issued")
    date = models.DateField(default=timezone.now)
    reason = models.TextField()
    severity = models.CharField(
        max_length=10,
        choices=[
            ("MINOR", "Minor"),
            ("MAJOR", "Major"),
        ],
        default="MINOR"
    )

    def __str__(self):
        return f"Warning for {self.employee} ({self.severity})"


class Suspension(models.Model):
    """
    Records a suspension period for an employee.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="suspensions")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="suspensions_approved")

    def __str__(self):
        return f"Suspension: {self.employee} ({self.start_date} - {self.end_date})"


class Investigation(models.Model):
    """
    Records an investigation into employee misconduct.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="investigations")
    initiated_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="investigations_initiated")
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    subject = models.CharField(max_length=200)
    findings = models.TextField(blank=True)
    outcome = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("CLEARED", "Cleared"),
            ("ACTION_TAKEN", "Action Taken"),
        ],
        default="PENDING"
    )

    def __str__(self):
        return f"Investigation: {self.employee} ({self.subject})"