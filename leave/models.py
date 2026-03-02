import logging
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from org.views import log_with_context
from org.models import TenantModel
from employees.models import Employee

from development.models import Appraisal
from decimal import Decimal
logger = logging.getLogger(__name__)
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db import transaction   
from org.views import log_with_context


class LeaveFrequency(TenantModel):
    """Annual, Monthly, Quarterly rules."""
    name = models.CharField(max_length=50)
    month_span = models.PositiveIntegerField(help_text="Span in months")

    class Meta:
        unique_together = ("tenant", "name")

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"

class LeaveType(TenantModel):
    name = models.CharField(max_length=100)
    is_paid = models.BooleanField(default=True)
    # annual_allocation = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    base_entitlement = models.PositiveIntegerField(
        default=0, # Added default to prevent IntegrityError
        help_text="Days per year"
    )
    carry_over_limit = models.PositiveIntegerField(default=5)
    requires_attachment = models.BooleanField(default=False, help_text="e.g., Sick leave needs a doctor's note")
    frequency = models.ForeignKey(LeaveFrequency, on_delete=models.SET_NULL, null=True, blank=True)
    block_leave_days = models.PositiveIntegerField(null=True, blank=True)
    is_event_based = models.BooleanField(default=False, help_text="For Maternity, Paternity, etc.")
    fixed_duration_value = models.PositiveIntegerField(null=True, blank=True, help_text="Duration value")
    duration_unit = models.CharField(
        max_length=10, 
        choices=[('DAYS', 'Days'), ('MONTHS', 'Months')], 
        default='DAYS'
    )
    class Meta:
        unique_together = ("tenant", "name")
        ordering = ["name"] # Order by name 
        
    def __str__(self):
        return f"{self.name} "


class LeaveRequest(TenantModel):
    STATUS_CHOICES =[
    ("pending", "Pending"), 
    ("rejected_for_amendment", "Rejected for Amendment"), 
    ("approved", "Approved"), 
    ("rejected", "Rejected")]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    approval_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="pending")
    attachment = models.FileField(upload_to="leave_attachments/", null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True)

    relief_employee = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="relief_requests",
        help_text="Employee who acts as relief durante this leave."
    )
    
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Audit fields
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name="approved_leaves")

    @property
    def duration(self):
        """Excludes weekends and tenant-specific public holidays."""
        from datetime import timedelta
        current_date = self.start_date
        working_days = 0
        
        while current_date <= self.end_date:
            # Check if it's a weekday (Monday=0 to Friday=4)
            if current_date.weekday() < 5:
                working_days += 1
            current_date += timedelta(days=1)
        
        # Subtract public holidays that fall on weekdays
        holidays = PublicHoliday.objects.filter(
            tenant=self.tenant, 
            date__range=(self.start_date, self.end_date)
        ).exclude(date__week_day__in=[6, 7])  # Exclude Saturday(6) and Sunday(7)
        
        return max(0, working_days - holidays.count())
    @property
    def duration_display(self):
        """Returns a string representation of the duration."""
        if self.leave_type.duration_unit == 'MONTHS':
            return f"{self.leave_type.fixed_duration_value} Month(s)"
        return f"{self.duration} Day(s)"
   
    def get_workflow_details(self):
        """Fetches the latest workflow action details (approver and comment)."""
        from workflow.models import WorkflowInstance
        from django.contrib.contenttypes.models import ContentType
        from datetime import timedelta
        
        try:
            ct = ContentType.objects.get_for_model(self)
            instance = WorkflowInstance.objects.filter(
                content_type=ct, 
                object_id=self.id
            ).order_by('-created_at').first()
            
            if not instance:
                return None
                
            # Get the latest decision action (Approve, Reject, or Request Amendment)
            latest_action = instance.actions.filter(
                action__in=['APP', 'REJ', 'AMD']
            ).order_by('-created_at').first()
            
            if latest_action:
                return {
                    'actor': latest_action.actor.full_name if latest_action.actor else "System",
                    'comment': latest_action.comment,
                    'status': latest_action.get_action_display()
                }
            
            # If pending and no actions yet
            if not instance.completed_at:
                approvers = instance.current_approvers.all()
                if approvers.exists():
                    names = ", ".join([a.full_name for a in approvers])
                    return {
                        'actor': names,
                        'comment': 'Awaiting action',
                        'status': 'Pending'
                    }
                # Fallback to stage approver type if no specific approvers assigned yet
                if instance.current_stage and instance.current_stage.approver_type:
                    return {
                        'actor': instance.current_stage.approver_type.name,
                        'comment': 'Awaiting action',
                        'status': 'Pending'
                    }
        except Exception as e:
            logger.error(f"Error in get_workflow_details: {str(e)}")
            return None
        return None


    def apply_workflow_changes(self, actor):
        """
        Called when the workflow reaches full approval.
        """
        self.approval_status = "approved"
        # Deduct leave balance
        self.deduct_from_balance()
        
        # If today is within leave period, mark employee as away
        today = timezone.now().date()
        if self.start_date <= today <= self.end_date:
            self.employee.work_status = 'L' # 'L' for ON_LEAVE
            self.employee.away = True
            self.employee.save()
            
        self.save()
        log_with_context(logging.INFO, f"Leave {self.id} approved and processed via workflow.", actor.user)

    def finalize_workflow(self, actor):
        """Compatibility method for WorkflowEngine."""
        self.apply_workflow_changes(actor)

    def clean(self):
        super().clean()
        if not self.start_date or not self.end_date:
            return
        # If employee not yet assigned, skip employee-dependent checks
        if not self.employee_id:
            return

        if self.end_date < self.start_date:
            raise ValidationError("End date cannot be before start date.")

        if self.leave_type.requires_attachment and not self.attachment:
            raise ValidationError("An attachment is required for this leave type.")

        balance = LeaveBalance.objects.filter(
            employee=self.employee,
            leave_type=self.leave_type,
            year=self.start_date.year
        ).first()

        if not balance or balance.balance_days < self.duration:
            raise ValidationError(
                f"Insufficient leave balance. Remaining: {balance.balance_days if balance else 0}"
            )
        
        
        # 1. Block Leave Enforcement
        # duration = self.duration # Uses your property
        # if duration >= 5 and self.leave_type.name != "Block Leave":
        #     # Check if company policy mandates Block Leave for this duration
        #     if self.tenant.has_block_leave_policy: # Conceptual flag
        #         raise ValidationError({
        #             "leave_type": "Policies mandate that leave of 5 days or more must be filed as 'Block Leave'."
        #         })
        # 1. Check for overlapping leave (Robust Conflict Check)
        overlapping_leave = LeaveRequest.objects.filter(
            employee=self.employee,
            approval_status__in=["pending", "approved"],
            start_date__lte=self.end_date,
            end_date__gte=self.start_date
        ).exclude(pk=self.pk)

        if overlapping_leave.exists():
            conflict = overlapping_leave.first()
            raise ValidationError(
                f"Date conflict: You already have a {conflict.leave_type.name} "
                f"request ({conflict.approval_status}) for this period."
            )

        # 2. Enforce Block Leave Policy
        # If any leave >= 5 days, or specific policy applies
        duration = (self.end_date - self.start_date).days + 1
        if self.leave_type.name != "Block Leave" and duration >= 5:
             # Logic to suggest or force conversion to Block Leave
             pass
    
    
    def save(self, *args, **kwargs):
        is_new_approval = False
        if self.pk:
            old_status = LeaveRequest.objects.get(pk=self.pk).approval_status
            if old_status != "approved" and self.approval_status == "approved":
                is_new_approval = True
        if self.leave_type.duration_unit == 'MONTHS' and self.leave_type.fixed_duration_value:
            if self.start_date and not self.end_date:
                self.end_date = self.start_date + relativedelta(months=self.leave_type.fixed_duration_value)
        
       
        
        super().save(*args, **kwargs)

        if is_new_approval:
            self.deduct_from_balance()

    def deduct_from_balance(self):
        """
        Consolidated logic for deducting leave. 
        Handles both Event-based (Maternity) and Standard (Annual) leave.
        """
        # Get or create the balance record for the current year
        balance, created = LeaveBalance.objects.get_or_create(
            employee=self.employee,
            leave_type=self.leave_type,
            year=self.start_date.year,
            tenant=self.tenant,
            defaults={'total_earned': 0, 'used': 0}
        )

        if self.leave_type.is_event_based:
            # For Maternity: We just track the 'used' days for reporting
            # We don't worry about 'total_earned' as it's not accrued
            balance.used += Decimal(self.duration)
        else:
            # For Annual/Sick: Standard deduction logic
            balance.used += Decimal(self.duration)
            # Optional: Update a cached balance_days if you still use that field
            if hasattr(balance, 'balance_days'):
                balance.balance_days -= Decimal(self.duration)

        balance.save()
        logger.info(f"Leave Deducted: {self.employee} used {self.duration} days of {self.leave_type.name}")
    
    @transaction.atomic
    def approve(self, actor):
        """
        Superior way: Handles status transition and employee work_status in one go.
        """
        try:
            self.status = "APPROVED"
            self.approved_by = actor
            self.save()
            
            # Logic: If start_date is today, update employee status immediately
            if self.start_date <= timezone.now().date():
                self.employee.work_status = 'ON_LEAVE' # Assuming choice exists
                self.employee.save()
                
            logger.info(f"LeaveRequest {self.id} approved by {actor.full_name}")
        except Exception as e:
            logger.error(f"Failed to approve LeaveRequest {self.id}: {str(e)}")
            raise
    
    def __str__(self):
        return f"{self.employee.first_name} {self.employee.last_name} -({self.leave_type.name})" 
    class Meta:
        # unique_together = ("tenant", "name")
        ordering = ["start_date"] # Order by name 


class LeaveBalance(TenantModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField(default=timezone.now().year)
    balance_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=5, decimal_places=2)
    used = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    @property
    def remaining(self):
        return self.total_earned - self.used
    
    @property
    def accrued_to_date(self):
        """
        Calculates how many days are earned from Jan 1st to today.
        Formula: (Total Earned / Days in Year) * Days Passed
        """
        today = date.today()
        if today.year > self.year: return self.total_earned # Past year fully earned
        if today.year < self.year: return Decimal('0.00')   # Future year not started
        
        day_of_year = today.timetuple().tm_yday
        days_in_year = 366 if (today.year % 4 == 0) else 365
        
        accrual = (self.total_earned / Decimal(days_in_year)) * Decimal(day_of_year)
        return accrual.quantize(Decimal('0.01'))

    class Meta:
        unique_together = ("employee", "leave_type", "year", "tenant")

class PublicHoliday(TenantModel):
    name = models.CharField(max_length=150)
    date = models.DateField()

    class Meta:
        unique_together = ("tenant", "date")
        
        
class HolidayPolicy(TenantModel):
    """
    Defines the rules for leave types per grade or department.
    """
    name = models.CharField(max_length=100) # e.g., "Standard Annual Leave Policy"
    leave_type = models.ForeignKey("leave.LeaveType", on_delete=models.CASCADE)
    
    # Accrual Logic
    accrual_rate = models.DecimalField(max_digits=5, decimal_places=3, help_text="Days earned per month")
    max_carry_over = models.DecimalField(max_digits=5, decimal_places=2, default=5, help_text="Max days to transfer to next year")
    
    # Probation Logic
    can_take_during_probation = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ("tenant", "name")

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"
    
    
class LeaveService:
    def __init__(self, tenant):
        self.tenant = tenant

    def initialize_yearly_balances(self, year=2026):
        employees = Employee.objects.filter(tenant=self.tenant, is_active=True)
        leave_types = LeaveType.objects.filter(tenant=self.tenant)
        
        count = 0
        for emp in employees:
            for lt in leave_types:
                # Base entitlement from LeaveType
                entitlement = Decimal(lt.base_entitlement)
                
                # Performance Bonus Logic
                # Check if they had a Grade A appraisal in the last cycle
                high_perf = Appraisal.objects.filter(
                    employee=emp, 
                    normalized_grade='A', 
                    status='COMPLETED'
                ).exists()
                
                if high_perf and lt.name == "Annual Leave":
                    entitlement += Decimal('2.0') # Bonus days
                
                LeaveBalance.objects.get_or_create(
                    tenant=self.tenant,
                    employee=emp,
                    leave_type=lt,
                    year=year,
                    defaults={'total_earned': entitlement}
                )
                count += 1
        return count