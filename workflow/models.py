from django.db import models, transaction
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import date, timedelta
import random
import logging
from decimal import Decimal
from django.conf import settings
from org.models import TenantModel, tenant_directory_path, JobRole, OrgUnit
from employees.models import Employee
from development.models import Appraisal
from notifications.models import Notification, NotificationService
from org.views import log_with_context

logger = logging.getLogger(__name__)


class WorkApprover(TenantModel):
    """
    Defines abstract approval roles (e.g., 'HR Manager', 'CFO').
    This decouples the Stage from a specific JobRole directly.
    """

    name = models.CharField(
        max_length=100, help_text="e.g., 'Line Manager 1', 'HR Officer', 'CFO'"
    )
    job_role = models.ForeignKey(
        JobRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The functional role associated with this approver type.",
    )

    class Meta:
        unique_together = ("tenant", "name")
        verbose_name = "Work Approver"

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"


class Workflow(TenantModel):
    """Defines a process (e.g., 'Annual Leave Process')"""

    name = models.CharField(
        max_length=100,
        help_text="Defines name of the workflow eg 'Annual Leave Process'",
    )
    code = models.SlugField(
        help_text="Defines code of the workflow eg 'leave-approval'"
    )  # e.g., 'leave-approval'
    description = models.TextField(help_text="Defines description of the workflow eg ")
    is_active = models.BooleanField(default=True)
    HIERARCHY_CHOICES = [
        ("MANAGER_CHAIN", "Follow Line Manager"),
        ("ROLE_BASED", "Strict Role Definition"),
        ("HYBRID", "Role within Manager Chain"),
    ]
    hierarchy_type = models.CharField(
        max_length=20, choices=HIERARCHY_CHOICES, default="MANAGER_CHAIN"
    )

    def __str__(self):
        return (
            f"{self.name} - code {self.code}"
        )

    class Meta:
        # ordering = ["last_name", "first_name"]
        verbose_name = "Workflow Record"
        verbose_name_plural = "Workflow Records"
        # indexes = [
        #     models.Index(fields=["first_name", "last_name", "tenant"]),
        #     models.Index(fields=["employee_email", "tenant"]),
        # ]
class WorkflowStage(TenantModel):
    """
    Represents a step in the workflow with time-based escalation logic.
    """

    workflow = models.ForeignKey(
        Workflow, on_delete=models.CASCADE, related_name="stages"
    )
    # Changed from CharField to ForeignKey as requested
    approver_type = models.ForeignKey(
        WorkApprover,
        on_delete=models.PROTECT,
        help_text="The designated approver role for this stage.",
        null=1,
        blank=True,
    )
    sequence = models.PositiveIntegerField(
        help_text="Order of execution (e.g., 1, 2, 3)"
    )
    turnaround_time = models.PositiveIntegerField(
        default=24, help_text="Maximum hours allowed for action before escalation."
    )
    is_final_stage = models.BooleanField(default=False)

    # Required for the Dashboard weight logic we built earlier
    required_authority_weight = models.IntegerField(default=0, editable=False)

    system_status = models.CharField(
        max_length=50,
        help_text="",
        null=True,
        blank=True,
    )
    APPROVAL_LOGIC = [
        ("ANY", "Any one can approve (Parallel)"),
        ("ALL", "All must approve (Sequential)"),
    ]
    approval_type = models.CharField(
        max_length=3, choices=APPROVAL_LOGIC, default="ANY"
    )
    is_conditional = models.BooleanField(default=False)

    class Meta:
        ordering = ["sequence"]
        unique_together = ("workflow", "sequence", "tenant")

    

    def clean(self):
        super().clean()
        if self.sequence < 1:
            raise ValidationError("Sequence must start from 1.")
        
        # Check for gaps in sequence within the same workflow
        existing_stages = WorkflowStage.objects.filter(
            workflow=self.workflow, 
            tenant=self.tenant
        ).exclude(pk=self.pk).values_list('sequence', flat=True)

        if existing_stages:
            max_seq = max(existing_stages)
            if self.sequence > max_seq + 1:
                raise ValidationError(f"Sequence is not consecutive. The next sequence should be {max_seq + 1}.")
        
        
        # earlier_final_stage = WorkflowStage.objects.filter(
        #     workflow=self.workflow,
        #     sequence__lt=self.sequence,
        #     is_final_stage=True,
        #     tenant=self.tenant
        # ).exists()

        # if earlier_final_stage:
        #     raise ValidationError(
        #         f"Cannot create stage {self.sequence}. A previous stage is already marked as the final stage."
        #     )
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        
    
    def __str__(self):
        return (
            f"{self.workflow.name} - Stage {self.sequence}: {self.approver_type.name}"
        )
    def savev1(self, *args, **kwargs):
        try:
            # Automate weight setting via the linked JobRole
            if self.approver_type.job_role and hasattr(
                self.approver_type.job_role, "authority_level"
            ):
                from workflow.services.workflow_engine import AUTHORITY_WEIGHTS

                self.required_authority_weight = AUTHORITY_WEIGHTS.get(
                    self.approver_type.job_role.authority_level, 0
                )
            super().save(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Error saving WorkflowStage {self.id}: {str(e)}", exc_info=True
            )
            raise
    # Inside WorkflowStage(TenantModel)
    
STATUS_CHOICES =[
        ("pending", "Pending"), 
        ("rejected_for_amendment", "Rejected for Amendment"), 
        ("approved", "Approved"), 
        ("rejected", "Rejected")]
class WorkflowInstance(TenantModel):
    """A live instance of a workflow (e.g., John Doe's Leave Request #402)"""

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, help_text="")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()  # ID of the LeaveRequest or Expense
    target = GenericForeignKey("content_type", "object_id")
    current_approvers = models.ManyToManyField(
        'employees.Employee', 
        blank=True, 
        related_name="pending_workflows"
    )
    current_stage = models.ForeignKey(WorkflowStage, on_delete=models.PROTECT)
    initiated_by = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="initiated_workflows"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    approval_ref = models.CharField(
        max_length=100, unique=True, blank=True, null=True, editable=False
    )
    approval_status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="pending"
    )

    def save(self, *args, **kwargs):
        # Apply the unique reference logic from your project
        if not self.approval_ref and (self.completed_at or self.approval_status == 'approved'):
            date_str = timezone.now().strftime("%Y%m%d")
            rand_suffix = str(random.randint(1000, 9999))
            self.approval_ref = f"{self.workflow.code.upper()}/{date_str}/{rand_suffix}"
            # self.approval_ref = f"/{date_str}/{rand_suffix}"
        super().save(*args, **kwargs)

    def track_history(self, actor, description, is_approved=None):
        """Narrative history log inspired by your previous project."""
        return HistoricalRecord.objects.create(
            tenant=self.tenant,
            instance=self,  # Linked to this workflow
            actor=actor,
            action_description=description,
            is_approved=is_approved,
        )
    # Inside class WorkflowInstance(TenantModel):

    # Inside class WorkflowInstance

  
    def move_to_next_stage(self):
        try:
            next_stage = WorkflowStage.objects.filter(
                workflow=self.workflow,
                sequence__gt=self.current_stage.sequence
            ).order_by('sequence').first()

            if not next_stage:
                return self.complete(actor=None)

            next_approvers = self.get_approver_for_stage(next_stage)
            
            # If the initiator is the approver, skip and notify
            if self.initiated_by in next_approvers:
                self.send_auto_approval_email(next_stage) # NEW
                self.track_history(None, f"System: Auto-approved stage {next_stage.sequence} (Requester is Approver).")
                
                self.current_stage = next_stage
                self.save()
                return self.move_to_next_stage() 

            self.current_stage = next_stage
            self.save()
            
        except Exception as e:
            logger.error(f"Error in move_to_next_stage: {e}", exc_info=True)

    def send_auto_approval_email(self, stage):
        """Sends a notification to the user that their request skipped a level."""
        subject = f"Auto-Approved: {self.workflow.name} - Stage {stage.sequence}"
        message = f"Your request {self.approval_ref} has been auto-approved at the '{stage.approver_type.name}' level because you are the designated approver."
        # send_mail(subject, message, 'hr@company.com', [self.initiated_by.employee_email])
    def get_approver_for_stage(self, stage, level_offset=0):
        """
        Logic 2b: Stage 3 -> Manager, Stage 5 -> Manager's Manager.
        """
        # 1. Direct Role Check
        if stage.approver_type and stage.approver_type.job_role and level_offset == 0:
            holders = Employee.objects.filter(grade__roles=stage.approver_type.job_role, tenant=self.tenant)
            if holders.exists(): return holders

        # 2. Sequential Hierarchy (Stage 1=Mgr, Stage 2=Grand-Mgr, etc.)
        target = self.initiated_by.line_manager
        # We climb up based on (sequence + offset)
        depth = stage.sequence + level_offset
        
        for _ in range(1, depth):
            if target and target.line_manager:
                target = target.line_manager
            else:
                break # CEO level reached
                
        return Employee.objects.filter(id=target.id) if target else Employee.objects.filter(is_hr_admin=True)
    
    
    @transaction.atomic
    def escalate_to_next_manager(self):
        """
        System-forced move up the chain due to turnaround_time breach.
        """
        try:
            # We look for the manager 1 level above the current sequence
            higher_approvers = self.get_approver_for_stage(self.current_stage, level_offset=1)
            
            approver_names = ", ".join([e.full_name for e in higher_approvers])
            
            # Log the escalation in history
            self.track_history(
                actor=None, 
                description=f"AUTO-ESCALATED: Responsibility shifted to {approver_names} due to SLA breach."
            )
            
            # If you have a 'current_assignee' field on the instance, update it here:
            # self.current_assignee = higher_approvers.first() 
            # self.save()

            log_with_context(logging.WARNING, f"Instance {self.approval_ref} escalated to {approver_names}", None)
            
        except Exception as e:
            logger.error(f"Escalation failed for Workflow {self.id}: {e}", exc_info=True)

    @transaction.atomic
    def complete(self, actor):
        """
        Generic completion logic that works for ANY model.
        """
        self.status = "APPROVED"
        self.completed_at = timezone.now()
        self.save()

        # Check if the target model has a custom finalization method
        # This makes it robust for Leave, Payroll, etc.

        # This is where we use the state name you requested
        if hasattr(self.target, "status"):
            self.target.status = "leave_application"
            
        if hasattr(self.target, "finalize_workflow"):
            try:
                self.target.finalize_workflow(actor)
                log_with_context(logging.INFO, f"Workflow {self.approval_ref} finalized by target logic.", actor.user)
            except Exception as e:
                logger.error(f"Finalization failed for {self.target}: {e}", exc_info=True)
                raise  # Rollback transaction if business logic fails
        
        self.track_history(actor, "Workflow completed successfully.", is_approved=True)
        logger.info(f"WorkflowInstance {self.id} completed by {actor.full_name}")

    @property
    def get_progress_data(self):
        stages = self.workflow.stages.all()
        history = self.actions.all()

        nodes = []
        for stage in stages:
            status = "pending"
            actor_name = stage.approver_type.name

            # Check if this stage was already completed
            action = history.filter(step=stage).first()
            if action:
                status = "completed" if action.action == "APP" else "rejected"
                actor_name = action.actor.full_name

            nodes.append(
                {
                    "name": stage.approver_type.name,
                    "status": status,
                    "actor": actor_name,
                    "is_current": (self.current_stage == stage),
                }
            )
        return nodes



    def __str__(self):
        return f"{self.workflow.name} for {self.target}"

    def get_approver_for_stagev1(self, stage, level_offset=0):
        """
        Calculates approver based on Stage Sequence + Offset.
        level_offset=0: Current intended approver.
        level_offset=1: The current approver's manager (Escalation).
        """
        # 1. If a specific Job Role is defined, try that first
        if stage.approver_type and stage.approver_type.job_role and level_offset == 0:
            holders = Employee.objects.filter(
                grade__roles=stage.approver_type.job_role,
                tenant=self.tenant,
                is_active=True
            )
            if holders.exists():
                return holders

        # 2. Hierarchy Logic: Start with the initiator's manager
        # Base depth is the stage sequence + any escalation offset
        depth = stage.sequence + level_offset
        
        target_approver = self.initiated_by.line_manager
        last_valid = target_approver

        for _ in range(1, depth):
            if target_approver and target_approver.line_manager:
                target_approver = target_approver.line_manager
                last_valid = target_approver
            else:
                # We hit the top of the Org Chart (e.g., CEO)
                target_approver = last_valid
                break

        if target_approver:
            return Employee.objects.filter(id=target_approver.id)

        # 3. Ultimate Fallback: HR Admin
        return Employee.objects.filter(is_hr_admin=True, tenant=self.tenant)
    def move_to_next_stagev1(self):
        """
        Finds the next stage, skipping if the initiator is the approver.
        """
        try:
            log_with_context(logging.INFO, f"Skipping Stage {next_stage.sequence}: Requester is approver.", None)
            next_stage = WorkflowStage.objects.filter(
                workflow=self.workflow,
                sequence__gt=self.current_stage.sequence
            ).order_by('sequence').first()
            log_with_context(logging.INFO, f"Skipping Stage {next_stage.sequence}: Requester is approver.", None)
            if not next_stage:
                return self.complete(actor=None) # Final Stage reached

            # Logic 2a: Check if Requester is the Approver for the next stage
            next_approvers = self.get_approver_for_stage(next_stage)
            if self.initiated_by in next_approvers:
                log_with_context(logging.INFO, f"Skipping Stage {next_stage.sequence}: Requester is approver.", None)
                self.current_stage = next_stage
                self.save()
                return self.move_to_next_stage() # Recursively check the next one

            self.current_stage = next_stage
            self.save()
            
        except Exception as e:
            logger.error(f"Error moving to next stage: {e}", exc_info=True)
    # Inside WorkflowInstance



class HistoricalRecord(TenantModel):
    instance = models.ForeignKey(
        WorkflowInstance, on_delete=models.CASCADE, related_name="history"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey("employees.Employee", on_delete=models.SET_NULL, null=True)
    action_description = models.TextField()
    is_approved = models.BooleanField(
        null=True,
        blank=True,
        help_text="True if action was an approval, False if rejection, None otherwise",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.instance.workflow.name} - {self.action_description[:30]}"



class WorkflowTransition(TenantModel):
    """The 'Arrows' between stages"""

    from_stage = models.ForeignKey(
        WorkflowStage, on_delete=models.CASCADE, related_name="outbound"
    )
    to_stage = models.ForeignKey(
        WorkflowStage,
        on_delete=models.CASCADE,
        related_name="inbound",
    )
    action_label = models.CharField(max_length=50)  # e.g., 'Approve'
    condition_logic = models.JSONField(
        null=True, blank=True
    )  # e.g., 'if amount > 5000'


class WorkflowAction(TenantModel):
    """
    Represents an action taken on a workflow step (approve, reject, comment).

    Attributes:
        instance (WorkflowInstance): The workflow instance this action belongs to.
        step (WorkflowStage): The step where the action was taken.
        actor (Employee): Employee who performed the action.
        action (str): The type of action (APP, REJ, COM).
        comment (str): Optional comment provided by the actor.
        created_at (datetime): Timestamp when the action was recorded.
    """

    ACTION_CHOICES = (
        ("APP", "Approve"),
        ("REJ", "Reject"),
        ("COM", "Comment"),
        ("AMD", "Request Amendment"),
    )

    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="actions",
        help_text="The workflow instance this action belongs to.",
    )
    step = models.ForeignKey(
        WorkflowStage,
        on_delete=models.CASCADE,
        help_text="The step where the action was taken.",
    )
    actor = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workflow_actions",
        help_text="Employee who performed the action.",
    )
    action = models.CharField(
        max_length=3,
        choices=ACTION_CHOICES,
        help_text="The type of action taken (Approve, Reject, Comment).",
    )
    comment = models.TextField(
        blank=True, help_text="Optional comment provided by the actor."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    # We use this to track 'Delegated' actions
    is_delegated = models.BooleanField(default=False)
    on_behalf_of = models.ForeignKey("employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_actions",
    )

    def __str__(self):
        return f"{self.instance} - {self.get_action_display()}"

class WorkflowCompatibleModel(TenantModel):
    """
    All models using the workflow should inherit from this 
    or implement these methods.
    """
    class Meta:
        abstract = True

    def finalize_workflow(self, actor):
        """Logic to execute when workflow is fully approved."""
        raise NotImplementedError("Subclasses must implement finalize_workflow")

    def reject_workflow(self, actor):
        """Logic to execute when workflow is rejected at any stage."""
        pass



class Delegation(TenantModel):
    """Allows 'Sarah' to act on behalf of 'Manager' for a set period."""

    delegator = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="delegations_given"
    )
    delegatee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="delegations_received"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    workflow_type = models.ForeignKey(
        Workflow,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Specific workflow or all if null",
    )

    def is_valid(self):
        return self.is_active and self.start_date <= date.today() <= self.end_date


class WorkflowDocument(TenantModel):
    """Supports versioning and multi-file attachments"""

    instance = models.ForeignKey(
        WorkflowInstance, on_delete=models.CASCADE, related_name="documents"
    )
    file = models.FileField(upload_to=tenant_directory_path)
    version = models.PositiveIntegerField(default=1)
    uploaded_by = models.ForeignKey("employees.Employee", on_delete=models.CASCADE, null=True)
    is_locked = models.BooleanField(
        default=False, help_text="Locked after final approval"
    )

    def create_new_version(self, new_file, user):
        """Allows replacing a document while incrementing version."""
        if self.is_locked:
            raise PermissionError("This document is locked and cannot be modified.")

        # Create a new record as the 'current' version
        return WorkflowDocument.objects.create(
            tenant=self.tenant,
            instance=self.instance,
            file=new_file,
            version=self.version + 1,
            uploaded_by=user,
        )


class WorkflowStagev1(TenantModel):
    """Specific steps in the workflow"""

    """
    Represents a single step in a workflow.

    Attributes:
        workflow (Workflow): The workflow this step belongs to.
        name (str): The name of the step (e.g., "Manager Approval").
        order (int): The order in which this step occurs.
        approver_role (str): Role of the approver (optional).
        approver_employee (Employee): Specific employee assigned as approver (optional).

    Example:
        >>> step = WorkflowStep.objects.create(
        ...     workflow=workflow,
        ...     name="Manager Approval",
        ...     order=1,
        ...     approver_role="Manager"
        ... )
        >>> str(step)
        'Leave Approval - Step 1: Manager Approval'
    """
    name = models.CharField(
        max_length=50,
        help_text="Defines name of the  sequence or stage eg 'Manager Approval' in the workflow.",
    )

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="stagesv1",
        help_text="The workflow this step belongs to.",
    )
    sequence = models.PositiveIntegerField(
        help_text="Defines the sequence of the step in the workflow. eg 1 for first step     "
    )

    required_role = models.ForeignKey(
        JobRole,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Defines the role required for this step eg 'Manager' in the workflow.",
    )
    is_final_stage = models.BooleanField(default=False)

    system_status = models.CharField(
        max_length=50,
        help_text="",
        null=True,
        blank=True,
    )
    APPROVAL_LOGIC = [
        ("ANY", "Any one can approve (Parallel)"),
        ("ALL", "All must approve (Sequential)"),
    ]
    approval_type = models.CharField(
        max_length=3, choices=APPROVAL_LOGIC, default="ANY"
    )
    is_conditional = models.BooleanField(default=False)

    # Dynamic Routing: If this is true, the system checks 'condition_logic'
    # This is the field we are automating
    required_authority_weight = models.IntegerField(default=0, editable=False)

    # Add this to store the numeric weight of the required authority
    def save(self, *args, **kwargs):
        from workflow.services.workflow_engine import AUTHORITY_WEIGHTS

        """
        Automatically sets the weight based on the required_role's authority level
        before saving to the database.
        """
        if self.required_role and hasattr(self.required_role, "authority_level"):
            # Fetch numeric value from our mapping (e.g., "APPROVER" -> 3)
            self.required_authority_weight = AUTHORITY_WEIGHTS.get(
                self.required_role.authority_level, 0
            )
        else:
            self.required_authority_weight = 0

        super().save(*args, **kwargs)

    class Meta:
        ordering = ["sequence"]

    def __str__(self):
        return f"{self.workflow.name} - Step {self.sequence}: {self.name}"
class InternalDocument(WorkflowCompatibleModel):
    """
    World-class internal document system supporting Memos, Policies, and Expenses.
    Integrates with the existing workflow engine.
    """
    DOC_TYPES = [
        ('MEMO', 'Internal Memo'),
        ('POLICY', 'Policy Document'),
        ('EXPENSE', 'Expense/Reimbursement'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('amendment', 'Rejected for Amendment'),
    ]

    doc_type = models.CharField(max_length=10, choices=DOC_TYPES, default='MEMO')
    subject = models.CharField(max_length=255)
    ref_no = models.CharField(max_length=100, unique=True, blank=True, null=True)
    sender_unit = models.ForeignKey('org.OrgUnit', on_delete=models.SET_NULL, null=True, related_name='sent_internal_docs')
    recipient = models.CharField(max_length=255, help_text="e.g., The Managing Director", blank=True, null=True)
    recipient_group = models.ForeignKey('auth.Group', on_delete=models.SET_NULL, null=True, blank=True, related_name='received_internal_docs')
    
    target_category = models.CharField(max_length=20, choices=[
        ('STAFF', 'Staff'),
        # ('FACULTY', 'Faculty'),
        ('VENDOR', 'Vendor'),
    ], default='STAFF')

    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Only for Expense docs")
    
    from tinymce.models import HTMLField
    content = HTMLField()
    original_content = HTMLField(blank=True, null=True) # Content at initiation
    reviewed_content = HTMLField(blank=True, null=True) # Content after reviewer edits
    
    attachment = models.FileField(upload_to='workflow/documents/', blank=True, null=True)
    
    # Participant Placeholders (for workflow routing)
    reviewer = models.ForeignKey('employees.Employee', on_delete=models.SET_NULL, null=True, related_name='reviewed_internal_docs')
    concurrence_list = models.ManyToManyField('employees.Employee', related_name='concurred_internal_docs', blank=True)
    approver_list = models.ManyToManyField('employees.Employee', related_name='approved_internal_docs_list', blank=True)
    final_approver = models.ForeignKey('employees.Employee', on_delete=models.SET_NULL, null=True, related_name='final_approved_internal_docs')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    initiator = models.ForeignKey('employees.Employee', on_delete=models.CASCADE, related_name='initiated_internal_docs')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Internal Document"
        verbose_name_plural = "Internal Documents"

    def __str__(self):
        return f"{self.get_doc_type_display()}: {self.subject} ({self.ref_no or 'Draft'})"

    def finalize_workflow(self, actor):
        """Logic executed when the workflow instance reaches final approval."""
        self.status = 'approved'
        if not self.ref_no:
            date_str = timezone.now().strftime("%Y%m%d")
            rand_suffix = str(random.randint(1000, 9999))
            self.ref_no = f"{self.doc_type}/{date_str}/{rand_suffix}"
        
        # Auto-create ProcurementRequest for approved expenses
        if self.doc_type == 'EXPENSE':
            try:
                ProcurementRequest.objects.create(
                    subject=f"Procurement for {self.subject}",
                    linked_document=self,
                    amount_total=self.amount or 0,
                    status='pending',
                    tenant=self.tenant
                )
                logger.info(f"ProcurementRequest auto-created for approved Expense: {self.subject}")
            except Exception as e:
                logger.error(f"Failed to auto-create ProcurementRequest: {str(e)}")
                
        self.save()

    def reject_workflow(self, actor):
        """Logic executed when the workflow is rejected."""
        self.status = 'rejected'
        self.save()





### Core Principles for Salesforce-like Modeling in Django


### Django Models (crm_core/models.py, sales/models.py, etc.)




class Activity(TenantModel):
    ACTIVITY_TYPE_CHOICES = [
        ('call', 'Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('task', 'Task'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('completed', 'Completed'),
        ('deferred', 'Deferred'),
    ]

    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES)
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Generic Foreign Key to link to Account, Contact, Lead, Opportunity, etc.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    related_to = GenericForeignKey('content_type', 'object_id')

    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_activities')
    
    # Salesforce-like audit fields
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_activities') # Often same as assigned_to
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_activities')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_activities')

    class Meta:
        verbose_name = "Activity (Task/Event)"
        verbose_name_plural = "Activities (Tasks/Events)"

    def __str__(self):
        return f"{self.activity_type}: {self.subject} ({self.status})"


# --- Procurement & Vendor Management ---

class Vendor(TenantModel):
    """
    World-class vendor management with compliance and rating.
    """
    name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    address = models.TextField()
    
    # Compliance
    compliance_docs = models.FileField(upload_to='vendors/compliance/', blank=True, null=True)
    tax_clearence_expiry = models.DateField(null=True, blank=True)
    
    # Terms
    payment_terms = models.CharField(max_length=100, default="Net 30")
    
    # Performance
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00) # 1.00 to 5.00
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"

    def __str__(self):
        return str(self.name)

class Asset(TenantModel):
    """
    Asset lifecycle management: Fixed vs Service.
    """
    ASSET_CLASSES = [
        ('FIXED', 'Fixed Asset (Equipment, Building)'),
        ('SERVICE', 'Recurring Service (Software License, Maintenance)'),
        ('LOGICAL', 'Logical Asset (Digital, IP)'),
    ]
    
    name = models.CharField(max_length=255)
    asset_class = models.CharField(max_length=10, choices=ASSET_CLASSES)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, related_name='assets')
    
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Lifespan rules
    expected_life_years = models.PositiveIntegerField(help_text="Expected lifespan in years")
    salvage_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    is_active = models.BooleanField(default=True)

    @property
    def current_book_value(self):
        # Basic straight-line depreciation calculation
        try:
            if not self.purchase_date:
                return Decimal("0.00")
            
            today = timezone.now().date()
            purchase_date = self.purchase_date
            # Ensure we're dealing with date objects for the subtraction
            if hasattr(purchase_date, 'date'):
                purchase_date = purchase_date.date() # type: ignore
            
            delta = today - purchase_date # type: ignore
            years_passed = delta.days / 365.25
            
            if years_passed >= self.expected_life_years:
                return Decimal(str(self.salvage_value))
            
            price = Decimal(str(self.purchase_price))
            salvage = Decimal(str(self.salvage_value))
            factor = Decimal(str(years_passed)) / Decimal(str(self.expected_life_years))
            depreciation = (price - salvage) * factor
            return price - depreciation
        except Exception as e:
            logger.error(f"Error calculating book value for Asset {self.name}: {str(e)}")
            return Decimal("0.00")

    class Meta:
        verbose_name = "Asset"
        verbose_name_plural = "Assets"

    def __str__(self):
        return str(self.name)

class ProcurementRequest(WorkflowCompatibleModel):
    """
    Links procurement to approved expense workflows.
    """
    subject = models.CharField(max_length=255)
    linked_document = models.ForeignKey(InternalDocument, on_delete=models.CASCADE, limit_choices_to={'doc_type': 'EXPENSE'})
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)
    
    amount_total = models.DecimalField(max_digits=15, decimal_places=2)
    vat_element = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    wht_element = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    invoice_attachment = models.FileField(upload_to='procurement/invoices/')
    
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def finalize_workflow(self, actor):
        self.status = 'approved'
        self.save()

    class Meta:
        verbose_name = "Procurement Request"
        verbose_name_plural = "Procurement Requests"
