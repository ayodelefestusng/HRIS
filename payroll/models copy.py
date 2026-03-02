from django.db import models

# Create your models here.
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from employees.models import Employee





from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


class AllowanceType(models.Model):
    """Defines global types of allowances (e.g., Housing, Transport)."""
    name = models.CharField(max_length=100, unique=True)
    is_taxable = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class GradeAllowance(models.Model):
    """Allowance amounts tied to a specific grade."""
    grade = models.ForeignKey("org.Grade", on_delete=models.CASCADE, related_name="allowances")
    allowance_type = models.ForeignKey(AllowanceType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("grade", "allowance_type")

    def __str__(self):
        return f"{self.grade.name} → {self.allowance_type.name} ({self.amount})"
    
    
class EmployeeAllowance(models.Model):
    """Custom recurring allowances for an employee."""
    CYCLE_CHOICES = [
        ("M", "Monthly"),
        ("Q", "Quarterly"),
        ("Y", "Yearly"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="custom_allowances")
    allowance_type = models.ForeignKey(AllowanceType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    cycle = models.CharField(max_length=3, choices=CYCLE_CHOICES, default="M")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("employee", "allowance_type")

    def __str__(self):
        return f"{self.employee} → {self.allowance_type.name} ({self.amount})"


class PayrollPeriod(models.Model):
    """Defines a payroll cycle (e.g., January 2026)."""
    name = models.CharField(max_length=100, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=3, choices=[("OPN", "Open"), ("CLO", "Closed")], default="OPN")

    
    def close_period(self):
        """Logic to finalize the period."""
        if self.status == "CLO":
            return False
            
        # Optional: Ensure all employees have entries before closing
        # Optional: Generate PDF payslips in bulk here
        
        self.status = "CLO"
        self.save()
        return True
    def __str__(self):
        return self.name
    
    
    
class PayrollEntry(models.Model):
    """Master payroll record for an employee in a given period."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payroll_entries")
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name="entries")
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    unique_together = ("employee", "period") # Essential safety check

    def calculate_totals(self):
        
        allowances = sum((item.amount for item in self.allowance_items.all()), Decimal('0.00'))
        deductions = sum((item.amount for item in self.deduction_items.all()), Decimal('0.00'))
        self.gross_salary = self.base_salary + allowances
        self.net_salary = self.gross_salary - deductions
        self.save()
        
    def save(self, *args, **kwargs):
        if self.period.status == "CLO":
            raise ValidationError("Cannot modify payroll entries for a closed period.")
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.employee} - {self.period.name}"


class PayrollAllowanceItem(models.Model):
    """Allowance line item in payroll."""
    entry = models.ForeignKey(PayrollEntry, on_delete=models.CASCADE, related_name="allowance_items")
    allowance_type = models.ForeignKey(AllowanceType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.allowance_type.name} ({self.amount})"


class Deduction(models.Model):
    """Types of deductions (e.g., Pension, Loan)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
    
class PayrollDeductionItem(models.Model):
    """Deduction line item in payroll."""
    entry = models.ForeignKey(PayrollEntry, on_delete=models.CASCADE, related_name="deduction_items")
    deduction = models.ForeignKey(Deduction, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.deduction.name} ({self.amount})"
    
    
class EmployeePayslip(models.Model):
    entry = models.OneToOneField(PayrollEntry, on_delete=models.CASCADE, related_name="payslip")
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payslip: {self.entry.employee} - {self.entry.period.name}"


class TaxRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE)
    payee = models.DecimalField(max_digits=12, decimal_places=2)
    nhis = models.DecimalField(max_digits=12, decimal_places=2)
    nhf = models.DecimalField(max_digits=12, decimal_places=2)

    def clean(self):
        if not self.employee.grade:
            raise ValidationError("Employee must have a grade to compute tax.")

    def __str__(self):  
        return f"Tax for {self.employee} - {self.period.name}"
    
    

class Reimbursement(models.Model):
    """
    Represents expense reimbursements requested by employees.
    Examples: travel expenses, medical claims.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="reimbursements")
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    request_date = models.DateField(default=timezone.now)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_reimbursements")
    processed_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee} - {self.amount} ({'Approved' if self.approved else 'Pending'})"


