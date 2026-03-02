
import logging
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from org.models import TenantModel
from employees.models import Employee

import logging
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from org.models import TenantModel

logger = logging.getLogger(__name__)

from django.utils import timezone
logger = logging.getLogger(__name__)

class AllowanceType(TenantModel):
    """
    Defines types of allowances. 
    World-class: We allow each tenant to define their own tax treatment for allowances.
    """
    name = models.CharField(max_length=100, help_text="e.g., Housing, Transport, Utility")
    is_taxable = models.BooleanField(default=True, help_text="If checked, this will be included in Pay-As-You-Earn (PAYE) calculations.")

    class Meta:
        unique_together = ("tenant", "name")

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"



class GradeAllowance(TenantModel):
    """
    Fixed allowances tied to a specific organizational grade.
    Help: Use this for standardized pay components like 'Housing' or 'Transport'.
    """
    grade = models.ForeignKey( "org.Grade", on_delete=models.CASCADE, related_name="grade_allowances")
    allowance_type = models.ForeignKey( AllowanceType, on_delete=models.CASCADE,help_text="The type of allowance (e.g., Utility, Transport).")
    amount = models.DecimalField(max_digits=12, decimal_places=2,help_text="The monthly amount for this grade level.")

    class Meta:
        # Ensures a grade doesn't have the same allowance type twice
        unique_together = ("grade", "allowance_type", "tenant")

    def __str__(self):
        return f"{self.grade.name} - {self.allowance_type.name}: {self.amount}"



class PayrollPeriod(TenantModel):
    """
    Defines the monthly/weekly window. 
    The 'leave_application' state logic can be applied here for periods pending final approval.
    """
    STATUS_CHOICES = [("OPN", "Open"), ("CLO", "Closed"), ("PND", "leave_application")]
    
    name = models.CharField(max_length=100, help_text="e.g., January 2026")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default="OPN")
    is_closed = models.BooleanField(default=False) # Once closed, slips are locked

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"



class PayrollEntry(TenantModel):
    """
    The snapshot of an employee's pay for a specific month.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="payroll_entries")
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name="entries")
    
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, help_text="Basic pay from employee grade.")
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ("employee", "period", "tenant")

    def calculate_totals(self):
        """
        Calculates Final Pay. 
        Formula: Gross = Base + Allowances; Net = Gross - Deductions
        """
        allowances = sum(item.amount for item in self.allowance_items.all())
        deductions = sum(item.amount for item in self.deduction_items.all())
        
        self.gross_salary = self.base_salary + allowances
        self.net_salary = self.gross_salary - deductions
        
        # Log calculation for audit
        logger.info(f"[PAYROLL] Calculated Net Pay for {self.employee}: {self.net_salary} (Tenant: {self.tenant.code})")
        self.save()

    def save(self, *args, **kwargs):
        if self.period.status == "CLO":
            raise ValidationError("Security Violation: Attempted to edit a closed payroll period.")
        
        # Auto-populate base_salary from Employee if it's a new entry
        if not self.pk and self.employee:
            self.base_salary = Decimal(self.employee.base_pay)
            
        super().save(*args, **kwargs)
        
 
 
        
class TaxRecord(TenantModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE)
    payee = models.DecimalField(max_digits=12, decimal_places=2)
    nhis = models.DecimalField(max_digits=12, decimal_places=2)
    nhf = models.DecimalField(max_digits=12, decimal_places=2)
    pension = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        # Prevent duplicate tax records for the same month/employee
        unique_together = ("employee", "period", "tenant")

    def clean(self):
        if not self.employee.grade:
            raise ValidationError("Employee must have a grade to compute tax.")
        
    def compute_taxes(self, gross_salary, basic_salary):
        """
        Populates the record with calculated statutory values.
        """
        # Move import here to prevent circular dependency
        from payroll.services.payroll_processing import TaxCalculator
        # Statutory: Pension 8% of Basic
        self.pension = basic_salary * Decimal('0.08')
        # NHF 2.5% of Basic
        self.nhf = basic_salary * Decimal('0.025')
        # NHIS 1.5% of Basic
        self.nhis = basic_salary * Decimal('0.015')   # 1.5%
        
        
        total_statutory = self.pension + self.nhf + self.nhis
        
        # Calculate PAYE using the service
        self.payee = TaxCalculator.calculate_paye(gross_salary, total_statutory)
        
        logger.info(f"[TAX] Computed for {self.employee}: PAYE={self.payee}, Pension={self.pension}")
        self.save()

    def __str__(self):  
        return f"Tax for {self.employee} - {self.period.name}"



class Deduction(TenantModel):
    """Types of deductions (e.g., Pension, Loan)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        # Enforce uniqueness per tenant only
        unique_together = ("tenant", "name")
    def __str__(self):
        return self.name
    
    
class PayrollDeductionItem(TenantModel):
    """Deduction line item in payroll."""
    entry = models.ForeignKey(PayrollEntry, on_delete=models.CASCADE, related_name="deduction_items")
    deduction = models.ForeignKey(Deduction, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.deduction.name} ({self.amount})"


class Payslip(TenantModel):
    employee = models.ForeignKey('employees.Employee', on_delete=models.CASCADE)
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE)
    
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2)
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2)
    
    generated_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = ('employee', 'period')
        
        
class PayslipLineItem(TenantModel):
    """Individual breakdown like 'Housing Allowance' or 'Income Tax'"""
    CATEGORY_CHOICES = [('EARNING', 'Earning'), ('DEDUCTION', 'Deduction')]
    
    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE, related_name='items')
    label = models.CharField(max_length=100) # e.g., 'Health Insurance'
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    
class EmployeePayslip(TenantModel):
    entry = models.OneToOneField(PayrollEntry, on_delete=models.CASCADE, related_name="payslip")
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payslip: {self.entry.employee} - {self.entry.period.name}"

class EmployeeAllowance(TenantModel):
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
        unique_together = ("employee", "allowance_type", "tenant")
        
    def __str__(self):
        return f"{self.allowance_type.name} ({self.amount})"
        



class PayrollAllowanceItem(TenantModel):
    """Allowance line item in payroll."""
    entry = models.ForeignKey(PayrollEntry, on_delete=models.CASCADE, related_name="allowance_items")
    allowance_type = models.ForeignKey(AllowanceType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.allowance_type.name} ({self.amount})"



class Reimbursement(TenantModel):
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


