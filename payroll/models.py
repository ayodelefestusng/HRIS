import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from employees.models import Employee
from org.models import Grade, TenantModel, expense_directory_path, tenant_directory_path

logger = logging.getLogger(__name__)
import logging
from django.db import models
from django.utils import timezone

from decimal import Decimal

logger = logging.getLogger(__name__)


class AllowanceType(TenantModel):
    ALLOWANCE_CHOICES = [
        ("GLOBAL", "Global Allowance"),
        ("GRADE", "Grade Allowance"),
        ("EXTRA", "Extra Allowance"),
    ]
    CYCLE_CHOICES = [
        ("BI_M", "Bi Monttly "),
        ("M", "Monthly"),
        ("BI_M_2", "Every Two Months "),
        ("Q", "Quarterly"),
        ("HY", "Half Year"),
        ("Y", "Yearly"),
    ]
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100, choices=ALLOWANCE_CHOICES)

    # New fields
    is_percentage = models.BooleanField(default=False)
    percentage_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage value if allowance is percentage-based",
    )
    cycle = models.CharField(max_length=100, choices=CYCLE_CHOICES, default="M")

    def clean(self):
        if self.is_percentage and not self.percentage_value:
            raise ValidationError(
                "Percentage value must be provided if is_percentage=True."
            )

    class Meta:
        unique_together = ("tenant", "name")

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class GradeAllowance(TenantModel):
    """
    Fixed allowances tied to a specific organizational grade.
    Help: Use this for standardized pay components like 'Housing' or 'Transport'.
    """

    grade = models.ForeignKey(
        Grade, on_delete=models.CASCADE, related_name="grade_allowances"
    )
    allowance_type = models.ForeignKey(
        AllowanceType,
        on_delete=models.CASCADE,
        help_text="The type of allowance (e.g., Utility, Transport).",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="The monthly amount for this grade level.",
    )

    class Meta:
        # Ensures a grade doesn't have the same allowance type twice
        unique_together = ("grade", "allowance_type", "tenant")

    def __str__(self):
        return f"{self.grade.name} - {self.allowance_type.name}: {self.amount}"


class GlobalAllowance(TenantModel):
    """
    Allowance given to all employees (e.g. Housing).
    """

    allowance_type = models.ForeignKey(AllowanceType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        # Ensures a grade doesn't have the same allowance type twice
        unique_together = ("allowance_type", "tenant")

    def __str__(self):
        return f"Global: {self.allowance_type.name}"


class ExtraAllowance(TenantModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="extra_allowances"
    )
    allowance_type = models.ForeignKey(AllowanceType, on_delete=models.CASCADE)

    is_percentage = models.BooleanField(default=False)
    percentage_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage value if allowance is percentage-based",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def clean(self):
        if self.is_percentage and not self.percentage_value:
            raise ValidationError(
                "Percentage value must be provided if is_percentage=True."
            )
        if not self.is_percentage and not self.amount:
            raise ValidationError(
                "Flat amount must be provided if is_percentage=False."
            )

    class Meta:
        # Ensures a grade doesn't have the same allowance type twice
        unique_together = ("employee", "allowance_type", "tenant")

    def __str__(self):
        return f"{self.employee} - {self.allowance_type.name}"


# -------------------------
# Deduction Types
# -------------------------
class DeductionType(TenantModel):
    """
    Defines deduction categories (Statutory, Grade, Extra).
    """

    DEDUCTION_CHOICES = [
        ("STATUTORY", "Statutory Deduction"),  # e.g. Tax, NHS
        ("GRADE", "Grade Deduction"),  # e.g. Union fees
        ("EXTRA", "Extra Deduction"),  # e.g. Employee-specific
    ]
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=DEDUCTION_CHOICES)

    is_percentage = models.BooleanField(default=False)
    percentage_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage value if deduction is percentage-based",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def clean(self):
        if self.is_percentage and not self.percentage_value:
            raise ValidationError(
                "Percentage value must be provided if is_percentage=True."
            )
        if not self.is_percentage and not self.amount:
            raise ValidationError(
                "Flat amount must be provided if is_percentage=False."
            )

    class Meta:
        # Ensures a grade doesn't have the same allowance type twice
        unique_together = ("name", "tenant")

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"



def calculate_payslip(employee, period):
    # 1. Basic Validation
    if period.status == "PD":
        raise ValidationError("Cannot recalculate a period that has already been PAID.")

    if not period.can_calculate:
        raise ValidationError("This period is closed and cannot be re-calculated.")

    if period.status == "CLO":
        raise ValidationError("Period is closed.")

    base_salary = Decimal(employee.base_pay)
    total_allowances = Decimal(0)
    # total_deductions = Decimal(0)

    # Create the Payslip object first
    # 2. Initialize/Update Payslip
    payslip, _ = Payslip.objects.update_or_create(
        employee=employee,
        period=period,
        tenant=employee.tenant,
        defaults={
            "basic_salary": base_salary,
            "gross_pay": base_salary,  # Temporary start
            "net_pay": base_salary,
        },
    )
    # Clear old line items if re-calculating
    payslip.items.all().delete()
    # -------------------------
    # Allowances
    # -------------------------
    # Global allowances

    # 2. Logic: Process Allowances (Example: Grade)

    for ga in GradeAllowance.objects.filter(
        grade=employee.grade, tenant=employee.tenant
    ):
        amt = (
            (ga.allowance_type.percentage_value / 100 * base_salary)
            if ga.allowance_type.is_percentage
            else ga.amount
        )
        PayslipLineItem.objects.create(
            payslip=payslip,
            label=ga.allowance_type.name,
            amount=amt,
            category="EARNING",
            tenant=employee.tenant,
        )
        total_allowances += amt

    # 4. Process Extra Allowances (New Line Items Added Here)
    for ea in ExtraAllowance.objects.filter(employee=employee, tenant=employee.tenant):
        amt = (
            (ea.percentage_value / 100 * base_salary) if ea.is_percentage else ea.amount
        )
        PayslipLineItem.objects.create(
            payslip=payslip,
            label=f"Extra: {ea.allowance_type.name}",
            amount=amt,
            category="EARNING",
            tenant=employee.tenant,
        )
        total_allowances += amt

    # 4. Process All Deductions (Using your helper function!)
    total_deductions = calculate_deductions(payslip)

    # 5. Final Calculation Update
    payslip.total_allowances = total_allowances
    payslip.total_deductions = total_deductions
    payslip.gross_pay = base_salary + total_allowances
    payslip.net_pay = payslip.gross_pay - total_deductions
    payslip.save()

    return payslip


def calculate_deductions(payslip):
    employee = payslip.employee
    tenant = payslip.tenant
    base_salary = payslip.basic_salary
    total_deductions = Decimal(0)

    # 1. Statutory Deductions (e.g., Tax, Pension)
    # These usually apply to everyone based on DeductionType percentage
    statutory = StatutoryDeduction.objects.filter(tenant=tenant)
    for sd in statutory:
        # Calculate based on the percentage defined in DeductionType or the override in StatutoryDeduction
        # Most tax/pension is calculated on Gross or Basic; here we use Basic
        amount = (sd.percentage / Decimal(100)) * base_salary

        PayslipLineItem.objects.create(
            payslip=payslip,
            label=sd.deduction_type.name,
            amount=amount,
            category="DEDUCTION",
            tenant=tenant,
        )
        total_deductions += amount

    # 2. Grade Deductions (e.g., Union Fees)
    grade_deductions = GradeDeduction.objects.filter(
        grade=employee.grade, tenant=tenant
    )
    for gd in grade_deductions:
        # Note: Added logic to handle both flat and percentage here
        amount = gd.amount  # Defaulting to the flat amount you have in your model

        PayslipLineItem.objects.create(
            payslip=payslip,
            label=gd.deduction_type.name,
            amount=amount,
            category="DEDUCTION",
            tenant=tenant,
        )
        total_deductions += amount

    # 3. Extra Deductions (Employee specific loans/penalties)
    extra = ExtraDeduction.objects.filter(employee=employee, tenant=tenant)
    for ed in extra:
        if ed.is_percentage:
            amount = (ed.percentage_value / Decimal(100)) * base_salary
        else:
            amount = ed.amount

        PayslipLineItem.objects.create(
            payslip=payslip,
            label=ed.deduction_type.name,
            amount=amount,
            category="DEDUCTION",
            tenant=tenant,
        )
        total_deductions += amount

    return total_deductions


class StatutoryDeduction(TenantModel):
    """
    Deduction applied to all employees (e.g. Tax).
    """

    deduction_type = models.ForeignKey(DeductionType, on_delete=models.CASCADE)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)  # e.g. 10%

    class Meta:
        # Ensures a grade doesn't have the same allowance type twice
        unique_together = ("deduction_type", "tenant")

    def __str__(self):
        return f"Statutory: {self.deduction_type.name}"


class GradeDeduction(TenantModel):
    """
    Deduction specific to employees in a grade (e.g. Union fee).
    """

    grade = models.ForeignKey(
        Grade, on_delete=models.CASCADE, related_name="deductions"
    )
    deduction_type = models.ForeignKey(DeductionType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        # Ensures a grade doesn't have the same allowance type twice
        unique_together = ("grade", "deduction_type", "tenant")

    def __str__(self):
        return f"{self.grade.name} - {self.deduction_type.name}"


class ExtraDeduction(TenantModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="extra_deductions"
    )
    deduction_type = models.ForeignKey(DeductionType, on_delete=models.CASCADE)

    is_percentage = models.BooleanField(default=False)
    percentage_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage value if deduction is percentage-based",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def clean(self):
        if self.is_percentage and not self.percentage_value:
            raise ValidationError(
                "Percentage value must be provided if is_percentage=True."
            )
        if not self.is_percentage and not self.amount:
            raise ValidationError(
                "Flat amount must be provided if is_percentage=False."
            )

    class Meta:
        # Ensures a grade doesn't have the same allowance type twice
        unique_together = ("employee", "deduction_type", "tenant")

    def __str__(self):
        return f"{self.employee} - {self.deduction_type.name}"


# -------------------------
# Payroll Period & Payslip
# -------------------------


class PayrollPeriod(TenantModel):
    """
    Defines the monthly/weekly window.
    The 'leave_application' state logic can be applied here for periods pending final approval.
    """

    # STATUS_CHOICES = [
    #     ("OPN", "open"),
    #     ("PND", "pending"),  # Pending Review
    #     ("CLO", "approved"),  # Calculations Locked
    #     ("PD", "paid"),  # Funds Disbursed
    # ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("rejected_for_amendment", "Rejected for Amendment"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("paid", "Paid"),
    ]
    
    name = models.CharField(max_length=100, help_text="e.g., January 2026")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    is_closed = models.BooleanField(default=False)  # Once closed, slips are locked

    class Meta:
        unique_together = ("name", "tenant")
        indexes = [
            models.Index(fields=["start_date", "end_date", "tenant"]),
            models.Index(fields=["status", "tenant"]),
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError("Start date cannot be after end date.")

            # Overlap Logic: (StartA <= EndB) and (EndA >= StartB)
            overlapping_periods = PayrollPeriod.objects.filter(
                tenant=self.tenant,
                start_date__lte=self.end_date,
                end_date__gte=self.start_date,
            )

            if self.pk:
                overlapping_periods = overlapping_periods.exclude(pk=self.pk)

            if overlapping_periods.exists():
                overlap = overlapping_periods.first()
                raise ValidationError(
                    f"Date range overlaps with existing period: {overlap.name} "
                    f"({overlap.start_date} to {overlap.end_date})"
                )

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

    @property
    def can_calculate(self):
        """Allows calculations in Open or Pending (leave_application) states."""
        return self.status in ["pending", "rejected_for_amendment"]

    @property
    def can_disburse_funds(self):
        """Funds can only be sent if status is Closed (Finalized).
        Prevents paying twice if already 'PD'."""
        return self.status == "approved"


class Payslip(TenantModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE)
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2)
    total_allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_pay = models.DecimalField(max_digits=12, decimal_places=2)

    generated_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    pdf_copy = models.FileField(upload_to=tenant_directory_path)

    class Meta:
        unique_together = ("employee", "period", "tenant")

    def calculate_totals(self):
        """
        Calculates Final Pay.
        Formula: Gross = Base + Allowances; Net = Gross - Deductions
        """
        total_deductions = sum(item.amount for item in self.deduction_items.all())
        self.base_salary = Decimal(self.employee.base_pay)
        self.gross_salary = self.base_salary + total_allowances
        self.net_pay = self.gross_salary - total_deductions

        # Log calculation for audit
        logger.info(
            f"[PAYROLL] Calculated Net Pay for {self.employee}: {self.net_pay} (Tenant: {self.tenant.code})"
        )
        self.save()

    def save(self, *args, **kwargs):
        if self.period.status == "CLO":
            raise ValidationError(
                "Security Violation: Attempted to edit a closed payroll period."
            )

        # Auto-populate base_salary from Employee if it's a new entry
        if not self.pk and self.employee:
            self.base_salary = Decimal(self.employee.base_pay)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.period.name},Pay Slip for {self.employee.first_name} -{self.employee.last_name} "

    # class Meta:
    #     unique_together = ('employee', 'period')


class PayrollEntry(TenantModel):
    """
    The snapshot of an employee's pay for a specific month.
    """

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="payroll_entries"
    )
    period = models.ForeignKey(
        PayrollPeriod, on_delete=models.CASCADE, related_name="entries"
    )

    base_salary = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Basic pay from employee grade."
    )
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ("employee", "period", "tenant")

    def calculate_totals(self):
        """
        Calculates Final Pay.
        Formula: Gross = Base + Allowances; Net = Gross - Deductions
        """
        allowances = sum(item.amount for item in self.items.filter(category="EARNING"))
        deductions = sum(
            item.amount for item in self.items.filter(category="DEDUCTION")
        )

        self.gross_salary = self.base_salary + allowances
        self.net_pay = self.gross_salary - deductions

        # Log calculation for audit
        logger.info(
            f"[PAYROLL] Calculated Net Pay for {self.employee}: {self.net_pay} (Tenant: {self.tenant.code})"
        )
        self.save()

    def save(self, *args, **kwargs):
        if self.period.status == "CLO":
            raise ValidationError(
                "Security Violation: Attempted to edit a closed payroll period."
            )

        # Auto-populate base_salary from Employee if it's a new entry
        if not self.pk and self.employee:
            self.base_salary = Decimal(self.employee.base_pay)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.period.name} Payroll Entries for {self.employee.first_name} -{self.employee.last_name} -{self.period.name} Paylip  "


class PayslipLineItem(TenantModel):
    """Individual breakdown like 'Housing Allowance' or 'Income Tax'"""

    CATEGORY_CHOICES = [("EARNING", "Earning"), ("DEDUCTION", "Deduction")]

    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE, related_name="items")
    label = models.CharField(max_length=100)  # e.g., 'Health Insurance'
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)

    class Meta:
        unique_together = ("payslip", "label", "category", "tenant")

    def __str__(self):
        return f"Line Items for  for {self.payslip.employee.first_name} -{self.payslip.employee.last_name}- {self.payslip.period}, Payslip"


class Reimbursement(TenantModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending Review"),
        ("APPROVED", "Approved (Pending Payroll)"),
        ("REJECTED", "Rejected"),
        ("PROCESSED", "Paid in Payroll"),
    ]

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="reimbursements"
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    receipt_image = models.ImageField(
        upload_to=expense_directory_path, null=True, blank=True
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    rejection_reason = models.TextField(blank=True, null=True)

    # Audit Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    processed_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        related_name="reimbursement_approvals",
    )

    def __str__(self):
        return f"{self.employee.full_name} - {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.pk:
            logger.info(
                f"[EXPENSE_CREATED] Tenant: {self.tenant.id} | "
                f"User: {self.employee.full_name} | "
                f"Amount: {self.amount} | "
                f"Path: {self.receipt_image.name if self.receipt_image else 'No Receipt'}"
            )
        super().save(*args, **kwargs)


class LoanRequest(TenantModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("REPAYING", "Repayment Active"),
        ("PAID_OFF", "Paid Off"),
    ]

    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE)
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    repayment_months = models.PositiveIntegerField(default=1)  # Duration of deduction

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    admin_notes = models.TextField(blank=True, null=True)

    # Tracking
    approved_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        related_name="loan_approvals",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def monthly_installment(self):
        return self.amount_requested / self.repayment_months


class AllowanceTypeTTT(TenantModel):
    """
    Defines types of allowances.
    World-class: We allow each tenant to define their own tax treatment for allowances.
    """

    name = models.CharField(
        max_length=100, help_text="e.g., Housing, Transport, Utility"
    )
    is_taxable = models.BooleanField(
        default=True,
        help_text="If checked, this will be included in Pay-As-You-Earn (PAYE) calculations.",
    )

    class Meta:
        unique_together = ("tenant", "name")

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"


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
        self.pension = basic_salary * Decimal("0.08")
        # NHF 2.5% of Basic
        self.nhf = basic_salary * Decimal("0.025")
        # NHIS 1.5% of Basic
        self.nhis = basic_salary * Decimal("0.015")  # 1.5%

        total_statutory = self.pension + self.nhf + self.nhis

        # Calculate PAYE using the service
        self.payee = TaxCalculator.calculate_paye(gross_salary, total_statutory)

        logger.info(
            f"[TAX] Computed for {self.employee}: PAYE={self.payee}, Pension={self.pension}"
        )
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

    entry = models.ForeignKey(
        PayrollEntry, on_delete=models.CASCADE, related_name="deduction_items"
    )
    deduction = models.ForeignKey(Deduction, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.deduction.name} ({self.amount})"


class EmployeePayslip(TenantModel):
    entry = models.OneToOneField(
        PayrollEntry, on_delete=models.CASCADE, related_name="payslip"
    )
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

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="custom_allowances"
    )
    allowance_type = models.ForeignKey(AllowanceType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    cycle = models.CharField(max_length=10, choices=CYCLE_CHOICES, default="M")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("employee", "allowance_type", "tenant")

    def __str__(self):
        return f"{self.allowance_type.name} ({self.amount})"


class PayrollAllowanceItem(TenantModel):
    """Allowance line item in payroll."""

    entry = models.ForeignKey(
        PayrollEntry, on_delete=models.CASCADE, related_name="allowance_items"
    )
    allowance_type = models.ForeignKey(AllowanceType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.allowance_type.name} ({self.amount})"
