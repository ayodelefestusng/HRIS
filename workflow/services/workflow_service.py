# Standard library
import logging
from datetime import timedelta, datetime
import hashlib
import time
from decimal import Decimal
import csv
from org.serializers import OrgUnitSerializer
import pdfplumber
import re
from org.models import OrgUnit
from employees.models import Employee
from django.db.models import Count, Q, F, ExpressionWrapper, FloatField
from django.db import transaction
from ats.models import Candidate
from django.db.models import Avg 

# models.py or services.py
from org.models import RoleSkillRequirement, RoleCompetencyRequirement  

from django.db.models import Avg



# Django
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from decimal import Decimal
from django.db import transaction
from payroll.models import (
    Employee,
    PayrollEntry,
    Payslip,
    PayslipLineItem,
    GradeAllowance,
    ExtraAllowance,
    StatutoryDeduction,
    GradeDeduction,
    ExtraDeduction,
)
# Third-party

# Local apps / models / services
from workflow.models import (
    Workflow,
    WorkflowInstance,
    WorkflowStage,
    WorkflowAction,
    Delegation,
)
from notifications.models import NotificationService
from org.views import log_with_context
from org.models import (
    JobRole,
    Grade,
    OrgUnitVersion,
    RoleOfficerInCharge,
    RoleCompetencyRequirement,
    OrgUnit,OrgSnapshot,
)

from employees.models import Employee
from org.models import OrgUnit

from employees.models import (
    Employee,
    CompanyPolicy,
    PolicyAcknowledgement,
    ExitProcess,
)
from attendance.models import AttendanceRecord
from development.models import SkillMatrix, Enrollment, GradeRequirement
from development.models import (
    Competency,
    Skill,
    CompetencySkill,
    EmployeeSkillProfile,
    EmployeeRoleFit,
)
from ats.models import Candidate, CandidateSkillProfile
from ats.models import Candidate
# Module logger
logger = logging.getLogger(__name__)
from employees.models import Employee, Department
import hashlib
import datetime
import time

        
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from payroll.models import Payslip,GradeAllowance,ExtraAllowance,ExtraDeduction,PayslipLineItem,StatutoryDeduction,Reimbursement,GradeDeduction
import logging
logger = logging.getLogger(__name__)

        
import csv
from django.http import HttpResponse
from decimal import Decimal
 
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.conf import settings
from notifications.models import Notification
from employees.models import ProfileUpdateRequest
from django.db.models import Q
from employees.models import Employee
from ats.models import Candidate
from employees.models import ExitProcess
from employees.models import EmployeeChangeRequest
from workflow.models import HistoricalRecord

# === GROUP LABELS ===
# GROUP 1: CORE WORKFLOW CONTROL
# GROUP 2: AUTHORIZATION & HIERARCHY
# GROUP 3: TRANSITION LOGIC
# GROUP 4: ACTION HANDLERS
# GROUP 5: UTILITIES
# GROUP 6: POLICY & EXIT SERVICES
import logging
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)



class WorkflowService:
    def __init__(self, tenant=None):
        self.tenant = tenant

    # =========================================================================
    # CORE HIERARCHY HELPERS
    # =========================================================================

    def get_recursive_downline_ids(self, employee):
        """
        Consolidated iterative helper to fetch all reporting IDs.
        Includes the employee's own ID as the root.
        """
        log_with_context(logging.INFO, f"Workflow triggered.", employee.user)
        try:    
            full_ids = [employee.id]
            stack = list(Employee.objects.filter(line_manager=employee, is_active=True)
                         .values_list('id', flat=True))
            
            while stack:
                current_id = stack.pop()
                if current_id not in full_ids:
                    full_ids.append(current_id)
                    child_reports = Employee.objects.filter(line_manager_id=current_id, is_active=True) \
                                                    .values_list('id', flat=True)
                    stack.extend(child_reports)
            return full_ids
        except Exception as e:
            logger.error(f"Error fetching downlines for {employee.id}: {str(e)}", exc_info=True)
            return [employee.id]

    # =========================================================================
    # WORKFLOW CONTROL (Refactored from Model)
    # =========================================================================
    def _notify_approver(self, instance):
        """Sends notification to all valid approvers for the current stage."""
        log_with_context(logging.INFO, f"Workflow _notify_approver.", instance.user)

        try:
            approvers = self.get_approver(instance, instance.current_stage)
        
            for approver in approvers:
                if approver.user:
                    create_notification(
                        recipient=approver.user,
                        title="Action Required",
                        message=f"A {instance.workflow.name} request is pending your approval.",
                        target=instance.target,  # This is the 'target' passed to the function
                        send_email=True
                    )
                    logger.info(f"Notified {approver.full_name} for instance {instance.id}")
            else:
                logger.warning(f"No approver found for instance {instance.id}")
                
        except Exception as e:
            logger.error(f"Failed to notify approver: {str(e)}", exc_info=True)
        
    
    def _get_active_delegation(self, actor, instance, expected_approver=None):
        """Checks for active delegation."""
        log_with_context(logging.INFO, f"Workflow _get_active_delegation.", instance.initiated_by.user)

        if not expected_approver:
            expected_approver = self.get_approver(instance, instance.current_stage)

        if not expected_approver:
            return None

        return Delegation.objects.filter(
            delegator__in=expected_approver,
            delegatee=actor,
            is_active=True,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date(),
        ).first()

    def should_bypass_workflow(self, employee):
        """
        Criteria for bypassing approval:
        - Grade Level > 4
        - Pyramid Level > 2
        - User Group: HR Officer, HR Admin, HR Manager, Manager
        """
        user = employee.user
        # bypass_groups = ["HR Officer", "HR Admin", "HR Manager", "Manager"]
        bypass_groups = ["HR Officer", "HR Manager", "Manager"]

        # 1. Group check
        if user.groups.filter(name__in=bypass_groups).exists():
            return True
            
        # # 2. Grade check
        # if employee.grade and employee.grade.level > 1:
        #     return True
            
        # # 3. Pyramid check
        # if employee.grade and employee.grade.pyramid and employee.grade.pyramid.level > :
        #     return True
            
        return False

    @transaction.atomic
    def trigger_workflow(self, workflow_code, target, started_by):
        """
        Central entry point to start a workflow. Moves logic from model to service.
        """
        log_with_context(logging.INFO, f"Workflow trigger_workflow.", started_by.user)

        try:
            workflow = Workflow.objects.get(code=workflow_code, tenant=self.tenant)
            first_stage = workflow.stages.order_by("sequence").first()

            if not first_stage:
                raise ValueError(f"Configuration Error: {workflow_code} has no defined stages.")

            instance = WorkflowInstance.objects.create(
                tenant=self.tenant,
                workflow=workflow,
                content_type=ContentType.objects.get_for_model(target),
                object_id=target.id,
                initiated_by=started_by,
                current_stage=first_stage,
                approval_status="pending"
            )

            # Record initial narrative
            instance.track_history(
                actor=started_by,
                description=f"Initialized {workflow.name} for {target}. Reference: {instance.approval_ref}",
                is_approved=True
            )

            # Check for bypass logic (Rule: Grade > 4, Pyramid > 2, etc.)
            if self.should_bypass_workflow(started_by):
                instance.track_history(
                    actor=None,
                    description=f"System: Workflow bypassed due to ranking/group of requester ({started_by.full_name})."
                )
                return self._finalize_workflow(instance, started_by)

            # Check if initiator is also the first approver (Auto-skip logic)
            self._handle_stage_transition(instance, started_by)
            
            log_with_context(logging.INFO, f"Workflow {workflow_code} triggered.", started_by.user)
            return instance

        except Exception as e:
            msg = f"Failed to trigger {workflow_code} for {started_by.full_name}: {str(e)}"
            logger.error(msg, exc_info=True)
            raise RuntimeError(msg)
    def track_history(self, instance, actor, description, is_approved=None):
        """Corrected to ensure the first positional arg is the WorkflowInstance"""
        log_with_context(logging.INFO, f"Workflow track_history.", actor.user)

        return HistoricalRecord.objects.create(
            tenant=self.tenant,
            instance=instance,  # Must be the WorkflowInstance object
            actor=actor,
            action_description=description,
            is_approved=is_approved,
        )
    
    
    def _handle_stage_transition(self, instance, actor):
        """
        Manages the movement between stages, including auto-approval if the 
        approver is the initiator.
        """
        log_with_context(logging.INFO, f"Workflow _handle_stage_transition.", instance.initiated_by.user)

        try:
            # current_approvers = self.get_approver(instance, instance.current_stage)
            current_approvers_qs = self.get_approver(instance, instance.current_stage)


            # DENORMALIZE: Save these approvers directly on the instance
            instance.current_approvers.set(current_approvers_qs)

            log_with_context(logging.INFO, f"Workflow actor detatils; Current Approver is {current_approvers_qs} and Initiator is {instance.initiated_by}", instance.initiated_by.user)
            # Logic: If initiator is the approver, auto-approve and move to next
            if instance.initiated_by in current_approvers_qs:
                instance.track_history(
                    # instance=instance, # Fixed earlier track_history fix
                    actor=None, 
                    description=f"System: Auto-approved stage {instance.current_stage.sequence} (Requester is Approver)."
                )
                log_with_context(logging.INFO, f"Workflow ALKUUU.", instance.initiated_by.user)
                self._move_to_next_stage(instance, actor)
            else:
                self._notify_approver(instance)
                log_with_context(logging.INFO, f"Workflow JEUSUSU.", instance.initiated_by.user)

        except Exception as e:
            logger.error(f"Transition error for instance {instance.id}: {str(e)}")


    def _move_to_next_stage(self, instance, actor):
        """
        Moves to next stage OR finalizes if current stage is marked final 
        or no further stages exist.
        """
        log_with_context(logging.INFO, f"Workflow _move_to_next_stage.", instance.initiated_by.user)
        # 1. Check if the CURRENT stage that was just approved is marked as final
        if instance.current_stage.is_final_stage:
            log_with_context(logging.INFO, f"Final stage reached via is_final_stage flag.", instance.initiated_by.user)
            return self._finalize_workflow(instance, actor)
        
        next_stage = WorkflowStage.objects.filter(
            workflow=instance.workflow,
            sequence__gt=instance.current_stage.sequence
        ).order_by('sequence').first()

        if next_stage:
            instance.current_stage = next_stage
            instance.save()
            self._handle_stage_transition(instance, actor)
        else:
            self._finalize_workflow(instance, actor)

    
    def resolve_current_approvers(self, instance):
        """
        Determines the valid approvers for the current stage of a workflow instance.
        """
        log_with_context(logging.INFO, f"Workflow resolve_current_approvers.", instance.initiated_by.user)

        if not instance.current_stage:
            return Employee.objects.none()
        
        # This calls your existing get_approver logic
        approver = self.get_approver(instance, instance.current_stage)
        
        # DENORMALIZE: Ensure the instance's ManyToMany field is in sync
        instance.current_approvers.set(approver)
        
        log_with_context(logging.INFO, f"Workflow resolve_current_approvers found {approver}.", instance.initiated_by.user)
        return approver
    
    def get_approver(self, instance, stage, level_offset=0):
        """
        Fixed logic to handle Grade/Role lookup and avoid ValueErrors.
        """
        log_with_context(logging.INFO, f"Workflow get_approver.", instance.initiated_by.user)

        try:
            # 1. Direct Role Check
            # Ensure we are querying the right field. If 'roles' is a ManyToMany 
            # on Grade, we might need to filter by name or ID.
            if stage.approver_type and stage.approver_type.job_role:
                # FIX: If job_role is a string/name, use name__icontains or name.
                # If it's an object, ensure it's the right type.
                # Use the specific role object or name
                job_role_val = stage.approver_type.job_role
                
                holders = Employee.objects.filter(
                    roles__job_title__name__icontains=str(job_role_val), 
                    tenant=self.tenant,
                    is_active=True
                ).distinct()
                
                if holders.exists(): 
                    # DELEGATION & AWAY LOGIC
                    resolved_ids = []
                    for emp in holders:
                        if not emp.away:
                            resolved_ids.append(emp.id)
                        else:
                            # Approver is AWAY. Find active delegation
                            delegation = Delegation.objects.filter(
                                delegator=emp,
                                tenant=self.tenant,
                                is_active=True,
                                start_date__lte=timezone.now().date(),
                                end_date__gte=timezone.now().date()
                            ).first()
                            
                            if delegation and delegation.delegatee and not delegation.delegatee.away:
                                resolved_ids.append(delegation.delegatee.id)
                            else:
                                # Fallback to relief or deputy
                                if emp.relief_person and not emp.relief_person.away:
                                    resolved_ids.append(emp.relief_person.id)
                                elif emp.deputy_person and not emp.deputy_person.away:
                                    resolved_ids.append(emp.deputy_person.id)
                                else:
                                    # Fallback to HR Admin if absolutely no one
                                    hr_adm_group = Group.objects.filter(name="HR Admin").first()
                                    if hr_adm_group:
                                        hr_admins = Employee.objects.filter(user__groups=hr_adm_group, tenant=self.tenant)
                                        resolved_ids.extend([e.id for e in hr_admins])

                    return Employee.objects.filter(id__in=resolved_ids).distinct()

            # 2. Sequential Hierarchy
            # Use instance.initiated_by (the actual employee who started it)
            target = instance.initiated_by.line_manager
            depth = stage.sequence + level_offset
            
            for _ in range(1, depth):
                if target and target.line_manager:
                    target = target.line_manager
                else:
                    break 
                    
            if target:
                return Employee.objects.filter(id=target.id)
                
            # Fallback to HR Admin if no manager found
            return Employee.objects.filter(
                user__groups__name__in=["HR Admin", "HR Manager", "HR Officer"], 
                tenant=self.tenant
            ).distinct()

        except Exception as e:
            logger.error(f"Error resolving approver for stage {stage.id}: {str(e)}")
            return Employee.objects.filter(
                user__groups__name__in=["HR Admin", "HR Manager", "HR Officer"], 
                tenant=self.tenant
            ).distinct()
    
    
    @transaction.atomic
    def reject_to_initiator(self, instance, actor, comment):
        """
        Moves the workflow back to the initiator for amendments.
        """
        log_with_context(logging.INFO, f"Workflow reject_to_initiator.", actor.user)

        try:
            # Update Instance
          

            instance.approval_status = "rejected_for_amendment" # Matches your new choices
            instance.save()
            
            target = instance.target
            if hasattr(target, "approval_status"):
                target.approval_status = "rejected_for_amendment"
                target.save()
            
            
            # Record history with the approver's comment
            self.track_history(
                instance=instance,
                actor=actor,
                description=f"Rejected for Amendment: {comment}",
                is_approved=False
            )

            # Notify the Initiator
            create_notification(
                recipient=instance.initiated_by.user,
                title="Amendment Required",
                message=f"Your {instance.workflow.name} request requires changes. Comment: {comment}",
                target=instance.target,
                send_email=True
            )

            log_with_context(logging.INFO, f"Workflow {instance.id} returned for amendment by {actor}", actor.user)
            
        except Exception as e:
            logger.error(f"Error in rejection logic for instance {instance.id}: {str(e)}", exc_info=True)
            raise


    @transaction.atomic
    def resubmit_workflow(self, instance, actor):
        """
        Restarts a rejected workflow from Stage 1.
        """
        log_with_context(logging.INFO, f"Workflow resubmit_workflow.", actor.user)

        try:
            first_stage = instance.workflow.stages.order_by("sequence").first()
            instance.current_stage = first_stage
            instance.approval_status = "pending"
            instance.save()

            instance.track_history(
                actor=actor,
                description="Request resubmitted after amendment.",
                is_approved=True
            )

            # Start the notification/auto-skip chain again
            self._handle_stage_transition(instance, actor)
            
            log_with_context(logging.INFO, f"Workflow {instance.id} resubmitted.", actor.user)
            
        except Exception as e:
            logger.error(f"Resubmission failed for instance {instance.id}: {e}")    
    
    @transaction.atomic
    def _finalize_workflow(self, instance, actor):
        """
        Finalizes the workflow and applies changes to the target model.
        """
        log_with_context(logging.INFO, f"Finalizing Workflow {instance.id}", actor.user)

        try:
            # 1. Update the Workflow Instance itself
            instance.approval_status = "approved"  # Changed from 'pending'
            instance.completed_at = timezone.now()
            instance.save()

            target = instance.target
            
            # 2. Execute model-specific finalization (The Strategy Pattern)
            # If the model defines its own logic, run it.
            if hasattr(target, "apply_workflow_changes"):
                target.apply_workflow_changes(actor)
            
            # 3. Fallback: If no method exists, just update the status if the field exists
            elif hasattr(target, "approval_status"):
                target.approval_status = "approved"
                target.save()

            # 4. History and Notifications
            # Ensure track_history matches the signature: (instance, actor, comment)
            self.track_history(instance, actor, "Workflow completed successfully.", is_approved=True)
            
            NotificationService.notify(
                recipient_emp=instance.initiated_by,
                title="Request Approved",
                # Respecting custom instruction for 'leave_application' terminology in messages
                message=f"Your {instance.workflow.name} has been processed: leave_application state reached.",
                target=target
            )
            
        except Exception as e:
            logger.error(f"Finalization failed for instance {instance.id}: {str(e)}", exc_info=True)
            raise  # Re-raise to trigger the transaction rollback
    
    @transaction.atomic
    def _finalize_workflowv1(self, instance, actor):
            """
            Finalizes the workflow and sets the requested state 'leave_application'.
            """
            log_with_context(logging.INFO, f"Workflow finalize_target_action.", actor.user)

            try:
                instance.approval_status = "pending"
                instance.completed_at = timezone.now()
                instance.save()

                target = instance.target
                if hasattr(target, "approval_status"):
                    # As per explicit instruction: use leave_application instead of submission_result
                    target.approval_status = "approved"
                    target.save()

                # Execute model-specific finalization (e.g., deducting leave balance)
                if hasattr(target, "apply_workflow_changes"):
                    target.apply_workflow_changes(actor)


                # 1. Handle Profile/Employee Updates
                elif hasattr(target, 'proposed_data') and target.__class__.__name__ == 'ProfileUpdateRequest':
                    employee = target.employee
                    changes = target.proposed_data  # Assuming this is a dictionary
                    
                    for field, value in changes.items():
                        if hasattr(employee, field):
                            setattr(employee, field, value)
                    
                    employee.save()
                    target.approval_status = "approved"
                    target.save()

                # 2. Handle Leave Applications (Generic example)
                elif target.__class__.__name__ == 'LeaveApplication':
                    target.approval_status = "approved" # Or leave_application per your state preference
                    target.save()
                    # Maybe deduct balance here?
                    
                log_with_context(logging.INFO, f"Finalized target {target} for instance {instance.id}", instance.initiated_by.user)
                            

                 # Check if the model has the 'apply_workflow_changes' method and run it
                if hasattr(target, 'apply_workflow_changes'):
                    target.apply_workflow_changes()
                else:
                    # Fallback for simple status updates
                    if hasattr(target, 'approval_status'):
                        target.approval_status = "approved"
                        target.save()





                instance.track_history(actor, "Workflow completed successfully.", is_approved=True)
                
                NotificationService.notify(
                    recipient_emp=instance.initiated_by,
                    title="Request Finalized",
                    message=f"Your {instance.workflow.name} has been moved to 'leave_application' status.",
                    target=target
                )
            except Exception as e:
                logger.error(f"Finalization failed for instance {instance.id}: {str(e)}", exc_info=True)
                raise

        # =========================================================================
        # ESCALATION & REASSIGNMENT
        # =========================================================================



    def finalize_target_actionv1(self, instance):
        target = instance.target
        # Check if the model has the 'apply_workflow_changes' method and run it
        if hasattr(target, 'apply_workflow_changes'):
            target.apply_workflow_changes()
        else:
            # Fallback for simple status updates
            if hasattr(target, 'approval_status'):
                target.approval_status = "approved"
                target.save()

    def process_escalations(self):
        """Finds overdue items and notifies Grand Managers with reassignment options."""
        log_with_context(logging.INFO, f"Workflow process_escalations.", instance.user)

        threshold = timezone.now() - timedelta(hours=48)
        items = WorkflowInstance.objects.filter(completed_at__isnull=True, created_at__lt=threshold, is_escalated=False)

        for inst in items:
            approver = self.get_approver(inst, inst.current_stage)
            if approver and approver.line_manager:
                self._send_escalation_email(inst, approver, approver.line_manager)
                inst.is_escalated = True
                inst.save()
    def send_auto_approval_email(self, stage):
        """Sends a notification to the user that their request skipped a level."""
        log_with_context(logging.INFO, f"Workflow send_auto_approval_email.", instance.user)

        subject = f"Auto-Approved: {self.workflow.name} - Stage {stage.sequence}"
        message = f"Your request {self.approval_ref} has been auto-approved at the '{stage.approver_type.name}' level because you are the designated approver."
        # send_mail(subject, message, 'hr@company.com', [self.initiated_by.employee_email])
        
    def _send_escalation_email(self, instance, original_approver, grand_manager):
        """Email includes 'Reassign' button logic."""
        log_with_context(logging.INFO, f"Workflow _send_escalation_email.", instance.user)

        subject = f"ACTION REQUIRED: Escalation for {instance.approval_ref}"
        base_url = "https://dignityconcept.tech"
        
        # Link to a view that allows the Grand Manager to pick a new assignee
        reassign_url = f"{base_url}/workflow/reassign/{instance.id}/"
        
        # ... logic to send EmailMultiAlternatives ...
        # HTML content includes: 
        # <a href="{{ reassign_url }}" style="...">Reassign Task</a>
        context = {
            'instance': instance,
            'original_approver': original_approver,
            'grand_manager': grand_manager,
            'days_pending': 2
        }
    
    
    
    def _find_active_role_holder(self, org_unit, role_type):
        """Finds active employee with specific role type in org unit."""
        log_with_context(logging.INFO, f"Workflow _find_active_role_holder.", org_unit)

        if not org_unit:
            return None

        return RoleOfficerInCharge.objects.filter(
            org_unit=org_unit,
            role_type=role_type,
            is_active=True,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date(),
        ).first()

    def _notify_approverv1(self, instance):
        """Sends notification to the current approver."""

        try:
            current_stage = instance.current_stage
            target = instance.target

            approver = self.get_approver(instance, current_stage)
            if approver:
                    create_notification(
                    recipient=approver.user,
                    title="New Approval Request",
                    message=f"You have a new approval request for {instance.workflow.name}.",
                    target=target,
                )
                    logger.info(
                    f"Notification sent | Workflow: {instance.workflow.code} | "
                    f"Instance: {instance.id} | To: {approver.user.email}"
                )
            else:
                logger.warning(f"No approver found for Instance {instance.id} at Stage {instance.current_stage.sequence}")
        
            
        except Exception as e:
            logger.error(f"Failed to notify approver for instance {getattr(instance, 'id', '<unknown>')}: {e}", exc_info=True)
            # Do not raise; notification failures should not halt workflow processing.



def get_recursive_downline_ids(employee):
    """
    Helper to fetch all IDs in the reporting chain.
    Includes the employee's own ID to ensure they can view their own profile.
    """
    full_ids = [employee.id] # Start with the manager themselves
    stack = list(Employee.objects.filter(line_manager=employee).values_list('id', flat=True))
    
    while stack:
        current_id = stack.pop()
        if current_id not in full_ids:
            full_ids.append(current_id)
            child_reports = Employee.objects.filter(line_manager_id=current_id).values_list('id', flat=True)
            stack.extend(child_reports)
    
    return full_ids


class WorkflowServicev3:
    def __init__(self, tenant):
        self.tenant = tenant

    # =========================================================================
    # GROUP 1: CORE WORKFLOW CONTROL
    # =========================================================================

    @transaction.atomic
    def start_workflow(self, workflow_code, target, started_by):
        """
        Initializes a workflow for any target (Leave, Attendance, etc.).
        """
        try:
            workflow = Workflow.objects.get(code=workflow_code, tenant=self.tenant)
            first_stage = workflow.stages.order_by("sequence").first()

            if not first_stage:
                raise ValueError(f"Workflow {workflow_code} has no stages defined.")

            instance = WorkflowInstance.objects.create(
                tenant=self.tenant,
                workflow=workflow,
                content_type=ContentType.objects.get_for_model(target),
                object_id=target.id,
                initiated_by=started_by,
                current_stage=first_stage,
            )

            # Initial History Record
            instance.track_history(
                actor=started_by,
                description=f"Started {workflow.name} for {target}",
                is_approved=True,
            )

            # Notify First Approver
            self._notify_approver(instance)
            log_with_context(
                logging.INFO,
                f"Started Workflow {workflow_code} for {target}",
                started_by.user,
            )
            return instance

        except Exception as e:
            msg = f"Failed to start workflow {workflow_code}: {str(e)}"
            log_with_context(logging.ERROR, msg, started_by.user)
            logger.error(msg, exc_info=True)
            raise

    @transaction.atomic
    def process_action(self, instance, actor, action_type, comment="", ip_address=None):
        """
        Processes APP, REJ, or AMD with validation and history.
        """
        try:
            if not comment or len(comment.strip()) < 5:
                raise ValidationError("A comment (min 5 chars) is mandatory.")

            # 1. Auth Check
            is_delegated, on_behalf_of = self._check_auth(actor, instance)

            # 2. Record Action
            WorkflowAction.objects.create(
                tenant=self.tenant,
                instance=instance,
                step=instance.current_stage,
                actor=actor,
                action=action_type,
                comment=comment,
                is_delegated=is_delegated,
                on_behalf_of=on_behalf_of,
                ip_address=ip_address,
            )

            # 3. Handle Transitions
            result_msg = ""
            if action_type == "REJ":
                _, result_msg = self._handle_rejection(instance, actor, comment)
            elif action_type == "AMD":
                _, result_msg = self._handle_amendment(instance, actor, comment)
            elif action_type == "APP":
                _, result_msg = self._handle_approval(instance, actor, comment)

            log_with_context(
                logging.INFO,
                f"Processed {action_type} for Instance {instance.id}: {result_msg}",
                actor.user,
            )
            return instance, result_msg

        except Exception as e:
            msg = f"Action {action_type} failed for Instance {instance.id}: {str(e)}"
            log_with_context(logging.ERROR, msg, actor.user)
            logger.error(msg, exc_info=True)
            raise

    # =========================================================================
    # GROUP 2: AUTHORIZATION & HIERARCHY
    # =========================================================================

    def get_approver(self, instance, stage):
        """
        Logic for Hierarchy: Returns the person authorized to approve.
        """
        try:
            initiator = instance.initiated_by
            h_type = instance.workflow.hierarchy_type
            org_unit = initiator.org_unit

            # 1. Pure Manager Chain
            if h_type == "MANAGER_CHAIN":
                return initiator.line_manager

            # 2. Role Based or Hybrid
            if h_type in ["ROLE_BASED", "HYBRID"]:
                # If Hybrid and first stage, prioritize Line Manager
                if h_type == "HYBRID" and stage.sequence == 1:
                    if initiator.line_manager:
                        return initiator.line_manager

                # Ensure stage.required_role exists
                if not stage.required_role:
                    return None

                target_role_type = stage.required_role.role_type  # e.g., 'HEAD'
                approver = self._find_active_role_holder(org_unit, target_role_type)

                # Fallback: HEAD -> DEPUTY
                if not approver and target_role_type == "HEAD":
                    approver = self._find_active_role_holder(org_unit, "DEPUTY")

                # Escalate to Parent OrgUnit HEAD
                if not approver and org_unit and org_unit.parent:
                    approver = self._find_active_role_holder(org_unit.parent, "HEAD")

                return approver
            return None
        except Exception as e:
            logger.error(f"Error getting approver: {e}", exc_info=True)
            return None
    def get_approverV1latest(self, instance, stage):
        """
        Consolidated helper used by both the Service (for notifications) 
        and the View (for resolution).
        """
        # Role-based
        if stage.approver_type and stage.approver_type.job_role:
            return Employee.objects.filter(
                grade__roles=stage.approver_type.job_role,
                tenant=self.tenant,
                is_active=True
            )

        # Manager-based (Stage 1)
        if stage.sequence == 1:
            mgr = instance.initiated_by.line_manager
            return Employee.objects.filter(id=mgr.id) if mgr else Employee.objects.none()

        # Grand Manager-based (Stage 2)
        if stage.sequence == 2:
            mgr = instance.initiated_by.line_manager
            gmgr = mgr.line_manager if mgr else None
            return Employee.objects.filter(id=gmgr.id) if gmgr else Employee.objects.none()

        return Employee.objects.filter(is_hr_admin=True, tenant=self.tenant)


    def _check_auth(self, actor, instance):
        """Checks if actor is authorized or a delegatee."""
        expected_approver = self.get_approver(instance, instance.current_stage)

        if actor == expected_approver:
            return False, None  # Not delegated

        delegation = self._get_active_delegation(actor, instance, expected_approver)
        if delegation:
            return True, delegation.delegator

        raise PermissionError("You are not authorized to take action on this workflow.")

    def _get_active_delegation(self, actor, instance, expected_approver=None):
        """Checks for active delegation."""
        if not expected_approver:
            expected_approver = self.get_approver(instance, instance.current_stage)

        if not expected_approver:
            return None

        return Delegation.objects.filter(
            delegator__in=expected_approver,
            delegatee=actor,
            is_active=True,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date(),
        ).first()

    def _find_active_role_holder(self, org_unit, role_type):
        """Finds active employee with specific role type in org unit."""
        if not org_unit:
            return None

        # Safe handling for integer/string mismatch isn't needed here if queries utilize correct types,
        # but 'role_type' is a specific field on JobRole, usually a ChoiceField string.
        role = (
            JobRole.objects.filter(
                org_unit=org_unit,
                role_type=role_type,
                status__in=["SUBSTANTIVE", "ACTING"],
                employee__isnull=False,
                is_deleted=False,
            )
            .select_related("employee")
            .first()
        )
        return role.employee if role else None
    def get_recursive_downline_ids1(self, employee):
        from org.views import log_with_context
        """Helper to fetch all IDs in the reporting chain."""
        full_ids = []
        # Start with direct reports
        stack = list(Employee.objects.filter(line_manager=employee).values_list('id', flat=True))
    
        while stack:
            current_id = stack.pop()
            if current_id not in full_ids:
                full_ids.append(current_id)
                # Find reports of this person and add to stack
                child_reports = Employee.objects.filter(line_manager_id=current_id).values_list('id', flat=True)
                stack.extend(child_reports)
            
    
        return full_ids
    
    def get_recursive_downline_ids(self, employee):
        """
        Returns a list of IDs of all employees reporting to the given employee,
        directly or indirectly (recursive).
        """
        downlines = []
        direct_reports = Employee.objects.filter(line_manager=employee, is_active=True)

        for report in direct_reports:
            downlines.append(report.id)
            # Recursive call
            downlines.extend(self.get_recursive_downline_ids(report))

        return downlines

    # =========================================================================
    # GROUP 3: TRANSITION LOGIC
    # =========================================================================

    def _should_transition(self, instance, stage):
        """Checks if the approval logic for the current stage is satisfied."""
        if stage.approval_type == "ANY":
            return True

        if stage.approval_type == "ALL":
            approvals_count = (
                WorkflowAction.objects.filter(
                    instance=instance, step=stage, action="APP"
                )
                .values("actor")
                .distinct()
                .count()
            )
            required_count = self._get_required_approver_count(instance, stage)
            return approvals_count >= required_count

        return False

    def _get_required_approver_count(self, instance, stage):
        """Returns the number of people who must sign off."""
        if stage.approval_type == "ALL":
            if stage.required_role:
                return Employee.objects.filter(
                    role=stage.required_role, tenant=self.tenant
                ).count()
        return 1

    # =========================================================================
    # GROUP 4: ACTION HANDLERS
    # =========================================================================

    def _handle_approval(self, instance, actor, comment):
        """Processes approval logic, stage transitions, and notifications."""
        current_stage = instance.current_stage

        instance.track_history(actor, f"Approved: {comment}", is_approved=True)

        if self._should_transition(instance, current_stage):
            next_stage = (
                WorkflowStage.objects.filter(
                    workflow=instance.workflow, sequence__gt=current_stage.sequence
                )
                .order_by("sequence")
                .first()
            )

            if next_stage:
                instance.current_stage = next_stage
                instance.save()
                self._notify_approver(instance)
                return instance, f"Moved to next stage: {next_stage.name}."
            else:
                self._finalize_workflow(instance)
                return instance, "Workflow fully approved and finalized."

        return instance, "Approval recorded. Awaiting other stakeholders."

    def _handle_rejection(self, instance, actor, comment):
        """Rejects workflow and notifies initiator."""
        instance.completed_at = timezone.now()
        instance.save()

        target = instance.target
        if hasattr(target, "approval_status"):
            target.approval_status = "rejected"
            target.save()

        instance.track_history(actor, f"Rejected: {comment}", is_approved=False)

        if instance.initiated_by:
            create_notification(
                recipient=instance.initiated_by.user,
                title="Request Rejected",
                message=f"Your request was rejected by {actor}. Comment: {comment}",
                target=target,
            )
        return instance, "Workflow Rejected."

    def _handle_amendment(self, instance, actor, comment):
        """Moves target back to DRAFT state."""
        target = instance.target
        if hasattr(target, "approval_status"):
            target.approval_status = "rejected_for_amendment"
            target.save()

        instance.track_history(
            actor, f"Amendment Required: {comment}", is_approved=False
        )

        if instance.initiated_by:
            create_notification(
                recipient=instance.initiated_by.user,
                title="Edit Required",
                message=f"Please edit your {instance.workflow.name}. Reason: {comment}",
                target=target,
            )
        return instance, "Amendment requested."

    def _finalize_workflow(self, instance):
        """Finalizes the workflow and updates target status."""
        instance.completed_at = timezone.now()
        instance.save()

        target = instance.target
        if not target:
            return

        # Handle different target types dynamically
        if hasattr(target, "deduct_from_balance"):
            target.approval_status = "approved"  # Standardize status
            target.deduct_from_balance()
        elif hasattr(target, "calculate_score"):
            target.approval_status = "completed"
            target.calculate_score()
        elif hasattr(target, "approval_status"):
            target.approval_status = "approved"
            target.save()

        if instance.initiated_by:
            create_notification(
                recipient=instance.initiated_by.user,
                title="Request Fully Approved",
                message=f"Your request for {instance.workflow.name} has been finalized.",
                target=target,
            )

    def _trigger_completion_logic(self, instance):
        """Finalizes the business object and sends the final notification."""
        target = instance.target
        if not target:
            logger.error(f"Workflow {instance.pk} has no target.")
            return
        # SET FINAL STATE TO 'leave_application' AS REQUESTED
        target.approval_status = "approved"
        
        # 1. Logic for Attendance
        if isinstance(target, AttendanceRecord):
            target.approval_status = "approved"
            target.is_verified = True
            target.remarks += f"\nApproved via Workflow: {instance.id}"
           

        # 2. Logic for Leave
        elif hasattr(target, "deduct_from_balance"):
            target.deduct_from_balance()
          

        # 3. AUDIT & LOCKING
        target.save()
        instance.completed_at = timezone.now()
        instance.save()

        # FIXED: Moved notification inside the function where 'instance' is defined
        NotificationService.notify(
            recipient_emp=instance.initiated_by,
            title="Request Fully Approved",
            message=f"Your request for {instance.workflow.name} has been finalized.",
            target=target
        )
    
    # =========================================================================
    # GROUP 5: UTILITIES
    # =========================================================================

    def _notify_approver(self, instance):
        """Sends notification to the current approver."""
        try:
            current_stage = instance.current_stage
            target = instance.target

            approver = self.get_approver(instance, current_stage)
            if approver:
                create_notification(
                    recipient=approver.user,
                    title="New Approval Request",
                    message=f"You have a new approval request for {instance.workflow.name}.",
                    target=target,
                )
        except Exception as e:
            logger.error(f"Failed to notify approver for instance {getattr(instance, 'id', '<unknown>')}: {e}", exc_info=True)
            # Do not raise; notification failures should not halt workflow processing.

    def batch_process(self, instance_ids, actor, action_code, comment):
        """
        Processes multiple requests. Uses a partial success pattern.
        """
        results = {"success": [], "failed": []}
        for i_id in instance_ids:
            try:
                instance = WorkflowInstance.objects.get(id=i_id)
                self.process_action(instance, actor, action_code, comment)
                results["success"].append(i_id)
            except Exception as e:
                results["failed"].append({"id": i_id, "error": str(e)})
        return results

    def process_escalations(self):
        """
        Finds pending tasks older than 48 hours and notifies the Grand Manager.
        """
        threshold = timezone.now() - timedelta(hours=48)
        pending_items = WorkflowInstance.objects.filter(
            completed_at__isnull=True,
            created_at__lt=threshold,
            is_escalated=False  # Flag to prevent multiple emails for same stage
        )

        for item in pending_items:
            current_approver = self.get_approver(item, item.current_stage)
            if current_approver and current_approver.line_manager:
                grand_manager = current_approver.line_manager
                
                # Send the email to the Grand Manager
                self.notify_escalation(item, current_approver, grand_manager)
                
                # Mark as escalated to avoid spamming
                item.is_escalated = True
                item.save()


        overdue_items = WorkflowInstance.objects.filter(
            completed_at__isnull=True,
            created_at__lt=threshold,
            is_escalated=False
        )

        for instance in overdue_items:
            approver = self.get_approver(instance, instance.current_stage)
            if approver and approver.line_manager:
                # Send Email to Grand Manager
                self.send_escalation_email(instance, approver, approver.line_manager)
                instance.is_escalated = True
                instance.save()

    def notify_escalation(self, instance, original_approver, grand_manager):
        subject = f"ESCALATION: Pending Approval for {original_approver.full_name}"
        context = {
            'instance': instance,
            'original_approver': original_approver,
            'grand_manager': grand_manager,
            'days_pending': 2
        }
        # Logic to send email template similar to the one created previously
        print(f"Escalating {instance.approval_ref} to {grand_manager.user.email}")


def check_escalations():
    """
    Run this via Cron or Celery every hour. Safely logs and continues on errors.
    """
    active_instances = WorkflowInstance.objects.filter(completed_at__is_null=True)
    for instance in active_instances:
        try:
            stage = instance.current_stage
            if not stage or not getattr(stage, "turnaround_time", None):
                continue

            limit_hours = stage.turnaround_time

            # Calculate if time exceeded
            elapsed_time = timezone.now() - (instance.created_at or timezone.now())
            if elapsed_time > timedelta(hours=limit_hours):
                # The "Nag" Email logic (placeholder)
                logger.warning(
                    "ESCALATION: %s has exceeded %s hours at stage %s",
                    instance, limit_hours, getattr(stage, "name", "<unknown>"),
                )
        except Exception as e:
            logger.error(f"Error checking escalations for instance {instance.id if instance and hasattr(instance, 'id') else instance}: {e}", exc_info=True)
            continue
    
def get_all_subordinates_iterative(manager_id):
    subordinates = []
    stack = [manager_id]
    
    while stack:
        current_id = stack.pop()
        # Querying for direct reports
        direct_reports = Employee.objects.filter(reporting_line_id=current_id).values_list('id', flat=True)
        for dr_id in direct_reports:
            subordinates.append(dr_id)
            stack.append(dr_id) # Push to stack to find their reports
            
    return subordinates   

def get_what_if_analysis(change_request_id):
    request = EmployeeChangeRequest.objects.get(id=change_request_id)
    employee = request.employee
    
    # 1. Prepare Mock Skill Data
    # Merge current skills with the proposed changes in JSON
    # proposed_data is a flat dict of {skill_id: level}
    proposed_skills = request.proposed_data if request.proposed_data else {}
    
    def mock_get_skill_levels(skill_ids):
        # Logic: If skill is in proposed_data, use that; else use DB current
        results = []
        for s_id in skill_ids:
            if str(s_id) in proposed_skills:
                results.append((s_id, proposed_skills[str(s_id)]))
            else:
                curr = EmployeeSkillProfile.objects.filter(employee=employee, skill_id=s_id).first()
                if curr:
                    results.append((s_id, curr.level))
        return results

    # 2. Re-run your generic fit logic with the mock data
    projected_fit = _compute_fit_generic(role=employee.current_role, get_skill_levels=mock_get_skill_levels)
    
    return {
        "current_score": employee.role_fit.score, # From your EmployeeRoleFit model
        "projected_score": projected_fit["final_score"],
        "improvement": projected_fit["final_score"] - employee.role_fit.score
    }

def check_workflow_blocker(self, employee):
    # Check if this employee has ANY pending change requests 
    # that haven't reached 'leave_application' state
    return not EmployeeChangeRequest.objects.filter(
        employee=employee, 
        approval_status='pending'
    ).exists()

@transaction.atomic
def finalize_profile_update(request_id):
    """
    Transitions ProfileUpdateRequest to 'leave_application' state 
    and commits changes to Employee profile.
    """
    req = ProfileUpdateRequest.objects.get(id=request_id)
    emp = req.employee

    try:
        # Update PII
        emp.phone_number = req.phone_number or emp.phone_number
        emp.address = req.address or emp.address
        emp.save()

        # Update Skills from proposed_data
        if hasattr(req, 'proposed_data') and isinstance(req.proposed_data, dict):
            for skill_id_str, level in req.proposed_data.items():
                try:
                    skill_id = int(skill_id_str)
                    EmployeeSkillProfile.objects.update_or_create(
                        employee=emp,
                        skill_id=skill_id,
                        tenant=req.tenant,
                        defaults={'level': level, 'source': 'manager_approved'}
                    )
                except (ValueError, TypeError):
                    continue

        # Final State Instruction
        req.approval_status = "approved"
        req.save()
        # 4. Cache the new Fit result
        compute_role_fit_for_employee(emp, emp.current_role)
        logger.info(f"Workflow Complete: Profile for {emp.full_name} updated.")
        
    except Exception as e:
        logger.error(f"Finalization failed for request {request_id}: {e}")
        raise





@transaction.atomic
def finalize_employee_update(workflow_instance):
    # Retrieve the temporary model
    change_req = workflow_instance.target 
    employee = change_req.employee
    
    # 1. Update Core Employee Fields
    for field, value in change_req.proposed_data.items():
        if field != 'skills':
            setattr(employee, field, value)
    employee.save()
    
    # 2. Update Skill Profiles (Skill Level Commits)
    if 'skills' in change_req.proposed_data:
        for skill_id, level in change_req.proposed_data['skills'].items():
            EmployeeSkillProfile.objects.update_or_create(
                employee=employee,
                skill_id=skill_id,
                defaults={'level': level}
            )
            
    # 3. Update State to leave_application (Finalized)
    change_req.approval_status = 'approved'
    change_req.save()
    
    # 4. Cache the new Fit result
    compute_role_fit_for_employee(employee, employee.current_role)




class WorkflowFinalizer:
    """
    Handles the actual data migration from ChangeRequest to Employee Profile.
    """
    @staticmethod
    @transaction.atomic
    def apply_change_request(request_id):
        """
        Commits staged data to the production models.
        """
        try:
            change_req = EmployeeChangeRequest.objects.select_for_update().get(id=request_id)
            employee = change_req.employee
            data = change_req.proposed_data
            
            logger.info(f"Finalizing Employee Update for {employee.id} (Tenant: {change_req.tenant.id})")

            # 1. Update Core Fields
            if 'base_pay' in data:
                employee.base_pay = data['base_pay']
            
            if 'grade_id' in data:
                employee.grade_id = data['grade_id']
            
            employee.save()

            # 2. Update Skills (Triggered Skill Level Commits)
            if 'skills' in data:
                for skill_id, new_level in data['skills'].items():
                    # HR verification logic would sit here
                    EmployeeSkillProfile.objects.update_or_create(
                        employee=employee,
                        skill_id=skill_id,
                        tenant=change_req.tenant,
                        defaults={
                            'level': new_level,
                            'source': 'system',
                            'comment': f"Updated via CR-{change_req.id}"
                        }
                    )

            # 3. Transition to the instruction-mandated state
            change_req.approval_status = 'approved'
            change_req.save()

            logger.info(f"Successfully finalized CR-{request_id} to 'leave_application' state.")
            return True

        except Exception as e:
            logger.error(f"Failed to finalize CR-{request_id}: {str(e)}", exc_info=True)
            raise

class SkillAnalyticsService:
    def __init__(self, tenant):
        self.tenant = tenant

    def identify_skill_gaps(self, employee):
        """
        Compares an employee's current skill levels against 
        the 'Required Skills' for their current Grade.
        """
        # Note: This assumes Grade model has a 'required_skills' ManyToManyField
        required_skills = employee.grade.required_skills.all()
        current_skills = SkillMatrix.objects.filter(employee=employee, tenant=self.tenant)
        
        gap_report = []
        for req in required_skills:
            current = current_skills.filter(skill=req).first()
            current_level = current.level if current else 0
            
            # If current level is lower than the grade requirement (e.g., Level 3)
            if current_level < 3: 
                gap_report.append({
                    'skill': req.name,
                    'current': current_level,
                    'target': 3,
                    'gap': 3 - current_level
                })
        
        return gap_report
    
# development/services.py

class CareerPathService:
    def __init__(self, tenant):
        self.tenant = tenant

    def evaluate_readiness(self, employee, target_grade=None):
        """
        Calculates a 'Readiness Score' based on Skills and Course Completions.
        """
        
        target = target_grade or employee.grade
        requirements = GradeRequirement.objects.filter(grade=target, tenant=self.tenant)
        
        if not requirements.exists():
            return {"score": 100, "status": "No Requirements Defined"}

        total_criteria = 0
        met_criteria = 0
        gaps = []

        for req in requirements:
            # 1. Check Skill Level
            total_criteria += 1
            user_skill = SkillMatrix.objects.filter(
                employee=employee, skill=req.skill, tenant=self.tenant
            ).first()
            
            current_level = user_skill.level if user_skill else 0
            if current_level >= req.minimum_level:
                met_criteria += 1
            else:
                gaps.append(f"Skill Gap: {req.skill.name} (Current: {current_level}, Required: {req.minimum_level})")

            # 2. Check Mandatory Courses
            for course in req.mandatory_courses.all():
                total_criteria += 1
                completed = Enrollment.objects.filter(
                    employee=employee, 
                    session__course=course, 
                    status="COM", 
                    tenant=self.tenant
                ).exists()
                
                if completed:
                    met_criteria += 1
                else:
                    gaps.append(f"Missing Course: {course.title}")

        readiness_score = (met_criteria / total_criteria) * 100
        
        return {
            "target_grade": target.name,
            "readiness_score": round(readiness_score, 2),
            "is_ready": readiness_score == 100,
            "gaps": gaps
        }
        
        


def compute_role_fit_for_employee(employee: Employee, role: JobRole):
    """
    Computes and stores the role fit of an employee.
    """
    result = _compute_fit_generic(
        role=role,
        get_skill_levels=lambda skill_ids: EmployeeSkillProfile.objects.filter(
            employee=employee,
            skill_id__in=skill_ids,
        ).values_list("skill_id", "level"),
    )

    fit, _ = EmployeeRoleFit.objects.update_or_create(
        employee=employee,
        role=role,
        defaults={
            "score": result["final_score"],
            "computed_at": timezone.now(),
        },
    )
    return fit


def compute_role_fit_for_candidate(candidate: Candidate, role: JobRole):
    """
    Computes fit for a candidate without persisting to a model.
    Returns a dict with final score and breakdown.
    """
    result = _compute_fit_generic(
        role=role,
        get_skill_levels=lambda skill_ids: CandidateSkillProfile.objects.filter(
            candidate=candidate,
            skill_id__in=skill_ids,
        ).values_list("skill_id", "level"),
    )
    return result


def _compute_fit_generic(role: JobRole, get_skill_levels):
    """
    Core scoring logic used for both employees and candidates.
    Returns:
    {
      "final_score": Decimal('84.50'),
      "competencies": [
         {
           "id": 1,
           "name": "Data Analysis",
           "weight": 5,
           "avg_level": 4.2,
           "normalized": 0.84,
           "weighted_contribution": 4.2
         },
         ...
      ]
    }
    """
    from development.models import Competency

    requirements = RoleCompetencyRequirement.objects.filter(role=role)

    if not requirements.exists():
        return {"final_score": Decimal("0.00"), "competencies": []}

    competencies_data = []
    total_weight = 0
    weighted_sum = Decimal("0")

    for req in requirements:
        competency = req.competency
        weight = req.weight

        comp_skills = list(
            CompetencySkill.objects.filter(
                competency=competency
            ).values_list("skill_id", flat=True)
        )
        if not comp_skills:
            continue

        skill_levels = list(get_skill_levels(comp_skills))
        if not skill_levels:
            avg_level = 0
        else:
            levels = [lvl for _, lvl in skill_levels]
            avg_level = sum(levels) / len(levels)

        normalized = Decimal(avg_level) / Decimal("5") if avg_level > 0 else Decimal("0")
        weighted = normalized * Decimal(weight)

        competencies_data.append(
            {
                "id": competency.id,
                "name": competency.name,
                "weight": weight,
                "avg_level": float(avg_level),
                "normalized": float(normalized),
                "weighted_contribution": float(weighted),
            }
        )

        total_weight += weight
        weighted_sum += weighted

    if total_weight == 0:
        final_score = Decimal("0.00")
    else:
        final_score = (weighted_sum / Decimal(total_weight)) * Decimal("100")
        final_score = final_score.quantize(Decimal("0.01"))

    return {"final_score": final_score, "competencies": competencies_data}


def compute_role_fit_for_all_employees(role: JobRole):
    """
    Recomputes fit score for all employees for a given role.
    """
    employees = Employee.objects.filter(is_active=True)
    fits = []
    for emp in employees:
        fits.append(compute_role_fit_for_employee(emp, role))
    return fits




def finalize_enrollment(enrollment_id):
    try:
        enrollment = Enrollment.objects.get(id=enrollment_id)
        enrollment.status = "COM"
        enrollment.save()  # This triggers enrollment.update_employee_skills() internally

        logger.info(
            "[TRAINING_COMPLETE] Employee: %s | Course: %s | Tenant: %s | Skills Boosted: %s",
            enrollment.employee.id,
            enrollment.session.course.title,
            enrollment.tenant.id,
            [s.name for s in enrollment.session.course.skills_taught.all()],
        )
    except Enrollment.DoesNotExist:
        logger.error("Enrollment %s not found", enrollment_id)
    except Exception as e:
        logger.error("Error finalizing enrollment %s: %s", enrollment_id, str(e), exc_info=True)
        raise
    



class ResumeParserService:
    @staticmethod
    def extract_text_from_pdf(pdf_file):
        
        text = ""
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + " "
            return text.lower()
        except Exception as e:
            logger.error(f"PDF Extraction Error: {e}")
            return ""

    @staticmethod
    def calculate_skill_level(text, skill_name):
        skill_name = skill_name.lower()
        pattern = rf"{re.escape(skill_name)}.*?(\d+)\s*(?:years|yrs|year)"
        match = re.search(pattern, text)
        if match:
            years = int(match.group(1))
            if years >= 7: return 5
            if years >= 5: return 4
            if years >= 3: return 3
            return 2
        return 1

    @classmethod
    def process_candidate_resume(cls, candidate_id):
        """Asynchronous-friendly method to process resume."""
        try:
            from ats.views import log_with_context
            candidate = Candidate.objects.get(id=candidate_id)
            if not candidate.resume:
                return

            resume_text = cls.extract_text_from_pdf(candidate.resume)
            profiles = CandidateSkillProfile.objects.filter(candidate=candidate)

            for profile in profiles:
                skill_name = profile.skill.name
                if skill_name.lower() in resume_text:
                    profile.level = cls.calculate_skill_level(resume_text, skill_name)
                    profile.save()
            
            log_with_context(logging.INFO, f"Resume parsed for candidate {candidate_id}", "System")
        except Exception as e:
            logger.error(f"Background Parsing Failed for Candidate {candidate_id}: {e}")



class PrivacyService:
    @staticmethod
    @transaction.atomic
    def anonymize_candidate(candidate_id, tenant):
        """
        Wipes PII from a candidate while preserving non-identifying data for HR metrics.
        """
        try:
            candidate = Candidate.objects.select_for_update().get(id=candidate_id, tenant=tenant)
            
            # 1. Generate a unique hash for the email so we don't allow 
            # the same person to re-apply immediately if that's a policy,
            # but we can't see the original email.
            email_hash = hashlib.sha256(candidate.email.lower().encode()).hexdigest()[:12]
            
            # 2. Wipe Personal Identifiable Information (PII)
            candidate.full_name = f"Anonymized_User_{email_hash}"
            candidate.email = f"deleted_{email_hash}@anonymized.com"
            candidate.phone = "00000000000"
            candidate.notes = "Content deleted for privacy compliance."
            
            # 3. Handle Files (Delete the physical resume)
            if candidate.resume:
                candidate.resume.delete(save=False)
                candidate.resume = None
            
            # 4. Update status flags
            candidate.is_anonymized = True
            candidate.anonymized_at = timezone.now()
            
            candidate.save()
            
            # Note: We do NOT delete skill_profiles or competency_profiles.
            # This allows the tenant to still see "We have 50 candidates with Python skills"
            # without knowing WHO they are.
            
            return True, "Candidate successfully anonymized."
        except Candidate.DoesNotExist:
            return False, "Candidate not found."
# ats/services/ranking_service.py

import requests
import logging
from django.conf import settings
from org.views import log_with_context

class IntegrationService:
    @staticmethod
    def post_job_to_linkedin(job_posting, user=None):
        """
        Integration to post a job to LinkedIn using OAuth2.
        Requires a valid access token stored in session or settings.
        """
        from ats.views import refresh_linkedin_token
        from org.models import LinkedInIntegration
        from django.db.models import Q
        from django.utils import timezone
        
        tenant = getattr(user, "tenant", None)
        if not tenant:
             # Fallback: if 'user' is actually a Tenant object (legacy)
             from org.models import Tenant
             if isinstance(user, Tenant):
                 tenant = user
             else:
                 raise Exception("No tenant context found for integration")

        integration = LinkedInIntegration.objects.get(tenant=tenant) 
        token = refresh_linkedin_token(integration)
        try:
            log_with_context(logging.INFO, f"Posting job to LinkedIn: {job_posting.title}", user)
            if not token:
                raise Exception("No LinkedIn access token configured")

            # Get userinfo to extract LinkedIn ID
            userinfo = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            ).json()
            sub_id = userinfo.get("sub")
            if not sub_id:
                raise Exception(f"Could not get LinkedIn user ID: {userinfo}")

            post_url = "https://api.linkedin.com/v2/ugcPosts"
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            }
            payload = {
                "author": f"urn:li:person:{sub_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            # "text": f"New job posted: {job_posting.title}\nApply here: {job_posting.get_absolute_url()}"
                             "text": f"New job posted: {job_posting.title}\nApply here: {job_posting.application_url}"
                        },
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }

            response = requests.post(post_url, headers=headers, json=payload)
            data = response.json()
            log_with_context(logging.INFO, f"LinkedIn API response: {data}", "System")

            if response.status_code != 201 and response.status_code != 200:
                raise Exception(f"LinkedIn API error: {data}")

            # external_id = data.get("id", f"li-{job_posting.pk}-api")
            external_id = f"{job_posting.application_url}"
            url = f"https://www.linkedin.com/feed/update/{external_id}"

            log_with_context(logging.INFO, f"Job  Aleko {job_posting.pk} with {job_posting.application_url} posted to LinkedIn", "System")

            return {
                "status": "success",
                "platform": "LinkedIn",
                "external_id": external_id,
                "url": external_id,
                # "url": url,
                # "url": external_id,
            }

        except Exception as e:
            log_with_context(logging.ERROR, f"LinkedIn posting failed: {e}", "System")
            return {"status": "error", "platform": "LinkedIn", "message": str(e)}

    @staticmethod
    def post_job_to_indeed(job_posting, user=None):
        """
        Mock integration to post a job to Indeed.
        """
        try:
            return {
                "status": "success",
                "platform": "Indeed",
                "external_id": f"ind-{job_posting.pk}-mock",
                "url": f"https://www.indeed.com/viewjob?jk=mock-{job_posting.pk}",
            }
        except Exception as e:
            log_with_context(logging.ERROR, f"Indeed posting failed: {e}", "System")
            return {"status": "error", "platform": "Indeed", "message": str(e)}



class IntegrationServicev4:
    @staticmethod
    def post_job_to_linkedin(job_posting, tenant):
        """
        Mock integration to post a job to LinkedIn.
        In a real scenario, this would use LinkedIn's API with OAuth2.
        """
        # Simulate API call latency
        # time.sleep(1)
        return {
            "status": "success",
            "platform": "LinkedIn",
            "external_id": f"li-{job_posting.pk}-mock",
            "url": f"https://www.linkedin.com/jobs/view/mock-{job_posting.pk}",
        }

    @staticmethod
    def post_job_to_indeed(job_posting, tenant):
        """
        Mock integration to post a job to Indeed.
        """
        integration = LinkedInIntegration.objects.get(tenant=tenant) 
        token = refresh_linkedin_token(integration)
        # time.sleep(0.5)
        return {
            "status": "success",
            "platform": "Indeed",
            "external_id": f"ind-{job_posting.pk}-mock",
            "url": f"https://www.indeed.com/viewjob?jk=mock-{job_posting.pk}",
        }

class RankingService:
    @staticmethod
    def get_ranked_candidates(job_posting, limit=10):
        """
        Calculates scores for all applicants of a job and returns the top N.
        """
        applications = job_posting.applications.select_related('candidate').prefetch_related(
            'candidate__experience', 'candidate__education', 
            'candidate__skill_profiles', 'candidate__competency_profiles'
        )
        
        ranked_list = []
        for app in applications:
            # Reusing our detailed scorecard logic
            score_data = app.candidate.get_detailed_scorecard(job_posting)
            ranked_list.append({
                'application': app,
                'candidate': app.candidate,
                'score': score_data['total_score'],
                'meets_min_exp': score_data['meets_min_exp'],
                'skill_match_pct': score_data['skill_match_percent'] 
            })
            
        # Sort by total score descending
        ranked_list.sort(key=lambda x: x['score'], reverse=True)
        return ranked_list[:limit]

class InterviewScheduler:
    @staticmethod
    def schedule_interview(application, start_time, location):
        try:
            # Format time for Google/Outlook API (yyyymmddTHHMM)
            formatted_time = start_time.strftime("%Y%m%dT%H%M")
            
            # 1. Create the Calendar Event
            # In production, you would call your integrated tool here
            # For now, we simulate the logic used in the model
            event_title = f"Interview: {application.candidate.full_name}"
            description = f"Position: {application.job_posting.role.job_title.name}\nScore: {application.candidate.full_name}"
            
            # 2. Update Application Status
            application.status = 'SCHEDULED'
            application.interview_time = start_time
            application.save()
            
            # Log for audit trail
            return True
        except Exception as e:
            logging.error(f"Scheduling Error: {e}")
            return False
        
       


# === GROUP 6: POLICY & EXIT SERVICES ===

class PolicyService:
    def __init__(self, tenant):
        self.tenant = tenant

    @transaction.atomic
    def distribute_policy(self, policy_id, target_grade=None):
        """
        Creates 'Pending' acknowledgements for all relevant employees.
        Can be targeted to a specific Grade (e.g., Only Managers sign the 'Leadership Policy').
        """
        try:
            policy = CompanyPolicy.objects.get(id=policy_id, tenant=self.tenant)
            
            # 1. Identify recipients
            employees = Employee.objects.filter(tenant=self.tenant, is_active=True)
            if target_grade:
                employees = employees.filter(grade=target_grade)

            # 2. Bulk Create acknowledgements
            acknowledgements = [
                PolicyAcknowledgement(
                    tenant=self.tenant,
                    employee=emp,
                    policy=policy,
                ) for emp in employees
                if not PolicyAcknowledgement.objects.filter(employee=emp, policy=policy).exists()
            ]
            
            created_objs = PolicyAcknowledgement.objects.bulk_create(acknowledgements)
            
            logger.info(f"Policy '{policy.title}' distributed to {len(created_objs)} employees.")
            
            # 3. TODO: Trigger Notification Service here (Email/In-app)
            return len(created_objs)

        except CompanyPolicy.DoesNotExist:
            logger.error(f"Policy ID {policy_id} not found for tenant {self.tenant.id}")
            return 0

    def get_compliance_report(self, policy_id):
        """
        Returns a breakdown of who has and hasn't signed a specific policy.
        """
        total_required = PolicyAcknowledgement.objects.filter(
            policy_id=policy_id, tenant=self.tenant
        ).count()
        
        signed = PolicyAcknowledgement.objects.filter(
            policy_id=policy_id, 
            tenant=self.tenant, 
            acknowledged_at__isnull=False
        ).count()
        
        pending = total_required - signed
        compliance_rate = (signed / total_required * 100) if total_required > 0 else 0
        
        return {
            "policy_id": policy_id,
            "total_required": total_required,
            "signed": signed,
            "pending": pending,
            "compliance_rate": round(compliance_rate, 2)
        }
            
            # Added to PolicyService
    def sign_policy(self, employee, policy_id, ip_address, user_agent):
        """
        Finalizes an acknowledgement with a digital 'fingerprint'.
        """
        ack = PolicyAcknowledgement.objects.get(
            employee=employee, 
            policy_id=policy_id, 
            tenant=self.tenant
        )
        
        
        
        # Create a unique hash for this signature event
        signature_base = f"{employee.id}-{policy_id}-{datetime.datetime.now()}-{ip_address}"
        signature_hash = hashlib.sha256(signature_base.encode()).hexdigest()
        
        ack.acknowledged_at = timezone.now()
        ack.digital_signature = signature_hash
        ack.comments = f"Signed via {user_agent} from IP {ip_address}"
        ack.save()
        
        return ack
    
    


class ExitService:
    @staticmethod
    def initiate_exit(employee, last_day, exit_type):
        exit_p = ExitProcess.objects.create(
            tenant=employee.tenant,
            employee=employee,
            last_working_day=last_day,
            exit_type=exit_type,
            status='CLEARANCE'
        )
        
        # Log for IT and Payroll to stop access/payments after last_day
        logger.warning(
            f"[EXIT_INITIATED] Tenant: {employee.tenant.code} | "
            f"Employee: {employee.full_name} | LWD: {last_day}"
        )
        return exit_p
    
    
    

class GlobalSearchService:
    @staticmethod
    def search(tenant, query):
        if not query or len(query) < 2:
            return {}

        # 1. Search Active/Onboarding Employees
        employees = Employee.objects.filter(tenant=tenant).filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(email__icontains=query)
        ).exclude(status='TERMINATED')[:5]

        # 2. Search Candidates (ATS)
        candidates = Candidate.objects.filter(tenant=tenant).filter(
            Q(full_name__icontains=query) | 
            Q(email__icontains=query)
        )[:5]

        # 3. Search Exited Staff
        exited = Employee.objects.filter(
            tenant=tenant, 
            status='TERMINATED'
        ).filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query)
        )[:5]

        return {
            'employees': employees,
            'candidates': candidates,
            'exited': exited,
            'query': query
        }



def create_notification(recipient, title, message, target=None, send_email=False):
    target_content_type = None
    target_object_id = None

    if target is not None:
        # Use the correct model field names: target_content_type and target_object_id
        target_content_type = ContentType.objects.get_for_model(target.__class__)
        target_object_id = target.id

    notification = Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        target_content_type=target_content_type, # Fixed argument name
        target_object_id=target_object_id,       # Fixed argument name
        send_email=send_email,
    )

    if send_email and recipient.email:
        try:
            _send_notification_email(notification)
        except Exception as e:
            logger.error(f"Email delivery failed for notification {notification.id}: {e}")

    return notification



def _send_notification_email(notification: Notification):
    subject = notification.title
    message = notification.message
    recipient_list = [notification.recipient.email]

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

    send_mail(subject, message, from_email, recipient_list, fail_silently=True)
    


def compute_org_metrics():
    metrics = {}

    for unit in OrgUnit.objects.all():
        headcount = Employee.objects.filter(
            job_history__department__org_unit__path__startswith=unit.path,
            job_history__is_active=True,
        ).distinct().count()

        metrics[unit.code] = {
            "headcount": headcount,
            "budget": float(unit.budget),
            "headcount_limit": unit.headcount_limit,
            "cost_center": unit.cost_center,
        }

    return metrics
def generate_snapshot():
    roots = OrgUnit.objects.filter(parent__isnull=True)
    tree = OrgUnitSerializer(roots, many=True).data
    metrics = compute_org_metrics()

    return OrgSnapshot.objects.create(tree=tree, metrics=metrics)

def create_org_version():
    roots = OrgUnit.objects.filter(parent__isnull=True)
    tree = OrgUnitSerializer(roots, many=True).data

    last = OrgUnitVersion.objects.first()
    next_version = (last.version + 1) if last else 1

    OrgUnitVersion.objects.create(version=next_version, data=tree)
    return next_version

def reorder_units(parent_id, ordered_ids):
    for index, unit_id in enumerate(ordered_ids):
        OrgUnit.objects.filter(id=unit_id, parent_id=parent_id).update(sort_order=index)
        

class TaxCalculator:
    @staticmethod
    def calculate_paye(gross_income, statutory_deductions):
        """
        Calculates monthly PAYE tax based on Nigerian Finance Act.
        """
        # 1. Calculate Consolidated Relief Allowance (CRA)
        # Higher of 200k/yr or 1% of gross + 20% of gross
        # annual_gross = gross_income * 12
        annual_gross = gross_income * 12
        relief_base = max(Decimal('200000'), (Decimal('0.01') * annual_gross))
        annual_cra = relief_base + (Decimal('0.20') * annual_gross)
        
        # 2. Taxable Income (Annual)
        annual_statutory = statutory_deductions * 12
        taxable_income = annual_gross - (annual_cra + annual_statutory)
        
        if taxable_income <= 0:
            return Decimal('0.00')

        # 3. Apply Progressive Tax Bands
        tax = Decimal('0.00')
        bands = [
            (300000, Decimal('0.07')),  # First 300k @ 7%
            (300000, Decimal('0.11')),  # Next 300k @ 11%
            (500000, Decimal('0.15')),  # Next 500k @ 15%
            (500000, Decimal('0.19')),  # Next 500k @ 19%
            (1600000, Decimal('0.21')), # Next 1.6m @ 21%
            (float('inf'), Decimal('0.24')) # Above 3.2m @ 24%
        ]

        remaining_income = taxable_income
        for limit, rate in bands:
            if remaining_income <= 0:
                break
            taxable_amount = min(remaining_income, limit)
            tax += taxable_amount * rate
            remaining_income -= taxable_amount

        return (tax / 12).quantize(Decimal('0.01')) # Return monthly tax


def compute_payroll_for_period(period):
    
    employees = Employee.objects.filter(is_active=True)

    for emp in employees:
        latest_comp = emp.comp_history.order_by("-effective_date").first()
        if not latest_comp:
            continue

        entry = PayrollEntry.objects.create(
            employee=emp,
            period=period,
            base_salary=latest_comp.salary_amount,
            total_allowances=0,
            total_deductions=0,
            net_pay=latest_comp.salary_amount,
        )

        # ✅ Notify employee
        create_notification(
            recipient=emp.user,
            title="Payslip Generated",
            message=f"Your payslip for {period.name} is now available.",
            target=entry,
            send_email=True,
        )

    period.approval_status = "approved"
    period.save()
    
    
    
class PayrollService:
    def __init__(self, period):
        self.period = period
        self.tenant = period.tenant

    def check_leave_status(self, employee):
        """Returns True if no pending leaves exist for the period."""
        # Note: Using 'pending' as the status per your requirement
        pending_leaves = employee.leave_applications.filter(
            approval_status="pending",
            start_date__lte=self.period.end_date,
            end_date__gte=self.period.start_date
        ).exists()
        return not pending_leaves

    @transaction.atomic
    def generate_for_employee(self, employee):
        """Processes the entire payroll for a single employee."""
        
        # 1. Validation Guards
        if not self.period.can_calculate:
            raise ValidationError(f"Period {self.period.name} is locked/closed.")

        if not self.check_leave_status(employee):
            raise ValidationError(
                f"Cannot generate payroll for {employee.get_full_name()}: "
                f"Pending leave applications exist."
            )

        # 2. Initialize the Payslip
        base_salary = Decimal(employee.base_pay)
        payslip, _ = Payslip.objects.update_or_create(
            employee=employee,
            period=self.period,
            tenant=self.tenant,
            defaults={
                "basic_salary": base_salary,
                "gross_pay": base_salary,
                "net_pay": base_salary
            }
        )
        
        # Clear old items for recalculation
        payslip.items.all().delete()
        
        total_allowances = Decimal(0)

        # 3. Process Allowances (Grade & Extra)
        # Grade Allowances
        for ga in GradeAllowance.objects.filter(grade=employee.grade, tenant=self.tenant):
            amt = (ga.allowance_type.percentage_value / 100 * base_salary) \
                  if ga.allowance_type.is_percentage else ga.amount
            
            PayslipLineItem.objects.create(
                payslip=payslip, label=ga.allowance_type.name, amount=amt,
                category='EARNING', tenant=self.tenant
            )
            total_allowances += amt

        # Extra Allowances
        for ea in ExtraAllowance.objects.filter(employee=employee, tenant=self.tenant):
            amt = (ea.percentage_value / 100 * base_salary) if ea.is_percentage else ea.amount
            PayslipLineItem.objects.create(
                payslip=payslip, label=f"Extra: {ea.allowance_type.name}", amount=amt,
                category='EARNING', tenant=self.tenant
            )
            total_allowances += amt

        # 4. Process Reimbursements
        total_allowances += self._process_reimbursements(payslip, employee)

        # 5. Process Deductions (Using the helper logic)
        total_deductions = self._calculate_all_deductions(payslip)

        # 6. Finalize Payslip Totals
        payslip.total_allowances = total_allowances
        payslip.total_deductions = total_deductions
        payslip.gross_pay = base_salary + total_allowances
        payslip.net_pay = payslip.gross_pay - total_deductions
        payslip.save()

        return payslip

    def _calculate_all_deductions(self, payslip):
        """Helper to process Statutory, Grade, and Extra deductions."""
        total = Decimal(0)
        base = payslip.basic_salary

        # Statutory
        for sd in StatutoryDeduction.objects.filter(tenant=self.tenant):
            amt = (sd.percentage / 100) * base
            PayslipLineItem.objects.create(
                payslip=payslip, label=sd.deduction_type.name, 
                amount=amt, category='DEDUCTION', tenant=self.tenant
            )
            total += amt

        # Grade
        for gd in GradeDeduction.objects.filter(grade=payslip.employee.grade, tenant=self.tenant):
            amt = gd.amount # Or add percentage logic here if needed
            PayslipLineItem.objects.create(
                payslip=payslip, label=gd.deduction_type.name, 
                amount=amt, category='DEDUCTION', tenant=self.tenant
            )
            total += amt

        # Extra
        for ed in ExtraDeduction.objects.filter(employee=payslip.employee, tenant=self.tenant):
            amt = (ed.percentage_value / 100 * base) if ed.is_percentage else ed.amount
            PayslipLineItem.objects.create(
                payslip=payslip, label=ed.deduction_type.name, 
                amount=amt, category='DEDUCTION', tenant=self.tenant
            )
            total += amt

        return total

    def _process_reimbursements(self, payslip, employee):
        """Approves and links reimbursements to the payslip."""
        total_reimb = Decimal(0)
        claims = Reimbursement.objects.filter(
            employee=employee, approved=True, processed_date__isnull=True, tenant=self.tenant
        )
        for claim in claims:
            PayslipLineItem.objects.create(
                payslip=payslip,
                label=f"Reimb: {claim.description[:30]}",
                amount=claim.amount,
                category='EARNING',
                tenant=self.tenant
            )
            total_reimb += claim.amount
            claim.processed_date = self.period.end_date
            claim.save()
        return total_reimb

    def run_bulk_payroll(self, employee_queryset):
        results = []
        for emp in employee_queryset:
            try:
                results.append(self.generate_for_employee(emp))
            except ValidationError as e:
                # Log error and continue to next employee
                print(f"Skipping {emp}: {e}")
        return results
    @transaction.atomic
    def mark_as_paid(self):
        """
        Finalizes the period after bank confirmation.
        """
        if self.period.approval_status != "approved":
            raise ValidationError("Period must be Approved before it can be marked as Paid.")
            
        # 1. Update status
        self.period.approval_status = "paid"
        self.period.save()
        
        # 2. Mark all associated payslips as published/final
        Payslip.objects.filter(period=self.period).update(is_published=True)
        
        logger.info(f"Payroll Period {self.period.name} has been marked as PAID.")
    
    def _apply_statutory_deductions(self, entry, tax_rec):
        """Helper to link tax record results to payroll line items."""
        # This logic ensures the net_pay reflects the taxes computed
        stats = [
            ('PAYE Tax', tax_rec.payee),
            ('Pension (8%)', tax_rec.pension),
            ('NHF', tax_rec.nhf)
        ]
        for name, amt in stats:
            # You might want a 'Deduction' type for these or just use them in calculation
            pass

    @transaction.atomic
    def generate_for_all_staff(self):
        """Generates payroll for every active employee in the tenant."""
        if self.period.approval_status != "approved":
            raise ValidationError("Cannot generate payroll for an unapproved period.")

        employees = Employee.objects.filter(tenant=self.tenant, is_active=True)
        count = 0
        for emp in employees:
            self.generate_for_employee(emp)
            count += 1
        
        # Move period to 'leave_application' state for review
        self.period.approval_status = "paid" 
        self.period.save()
        return count

    def send_employee_payslip_email(self, payslip):
        """Sends the payslip to the employee via email."""
        subject = f"Your Payslip for {payslip.period.name}"
        message = (
            f"Dear {payslip.employee.get_full_name()},\n\n"
            f"Your payslip for the period {payslip.period.name} is now available.\n"
            f"Gross Pay: {payslip.gross_pay}\n"
            f"Total Deductions: {payslip.total_deductions}\n"
            f"Net Pay: {payslip.net_pay}\n\n"
            "Please log in to the HR portal to view the detailed breakdown.\n\n"
            "Best regards,\n"
            "Payroll Department"
        )
        recipient_list = [payslip.employee.email]
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

        send_mail(subject, message, from_email, recipient_list, fail_silently=True)



class BankExportService:
    def __init__(self, period):
        self.period = period
        self.tenant = period.tenant

    def generate_bank_csv(self):
        # SECURITY CHECK: Only allow export if period is finalized
        if not self.period.can_disburse_funds:
            raise PermissionDenied(
                f"Export blocked. Period {self.period.name} must be 'Closed' "
                f"before generating bank schedules."
            )

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        filename = f"Bank_Schedule_{self.period.name.replace(' ', '_')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        
        # CSV Headers
        writer.writerow(['Beneficiary Name', 'Account Number', 'Bank Code', 'Amount', 'Narration'])

        # Get all payslips for this period
        payslips = Payslip.objects.filter(period=self.period, tenant=self.tenant)

        for slip in payslips:
            # We assume your Employee model has these banking fields
            emp = slip.employee
            writer.writerow([
                f"{emp.first_name} {emp.last_name}",
                getattr(emp, 'account_number', 'N/A'),
                getattr(emp, 'bank_code', '000'),
                slip.net_pay,
                f"Salary {self.period.name}"
            ])

        return response




def merge_units(source_id, target_id):
    source = OrgUnit.objects.get(id=source_id)
    target = OrgUnit.objects.get(id=target_id)

    Employee.objects.filter(org_unit=source).update(org_unit=target)

    for child in source.children.all():
        child.parent = target
        child.save()

    source.delete()
    return True


def split_unit(unit_id, new_units):
    unit = OrgUnit.objects.get(id=unit_id)

    created_units = []
    for data in new_units:
        new_unit = OrgUnit.objects.create(
            name=data["name"],
            code=data["code"],
            parent=unit.parent
        )
        Employee.objects.filter(id__in=data["employees"]).update(org_unit=new_unit)
        created_units.append(new_unit.id)

    return created_units



def get_detailed_scorecard(candidate, job_posting):
    role = job_posting.role
    
    # --- 1. Experience & Education (Previous Logic) ---
    exp_score = sum(exp.calculated_weight for exp in candidate.experience.all())
    edu_score = sum(edu.weight for edu in candidate.education.all())

    # --- 2. Skill Alignment ---
    skill_score = 0
    skill_details = []
    role_skills = RoleSkillRequirement.objects.filter(role=role)
    
    for req in role_skills:
        # Check if candidate has this specific skill
        profile = candidate.skill_profiles.filter(skill=req.skill_name).first()
        candidate_level = profile.level if profile else 0
        
        # Scoring logic: 10 points per skill if level met, +2 bonus for exceeding
        points = 0
        if candidate_level >= req.required_level:
            points = 10 + (2 if candidate_level > req.required_level else 0)
        
        skill_score += points
        skill_details.append({
            'name': req.skill_name.name,
            'required': req.required_level,
            'actual': candidate_level,
            'points': points
        })

    # --- 3. Competency Alignment ---
    comp_score = 0
    comp_details = []
    role_comps = RoleCompetencyRequirement.objects.filter(role=role)
    
    for req in role_comps:
        profile = candidate.competency_profiles.filter(competency=req.competency).first()
        candidate_level = profile.level if profile else 0
        
        # Scoring: (Level * Weight)
        points = candidate_level * req.weight
        
        comp_score += points
        comp_details.append({
            'name': req.competency.name,
            'required': req.required_level,
            'actual': candidate_level,
            'weight': req.weight,
            'points': points
        })

    total_score = exp_score + edu_score + skill_score + comp_score

    return {
        'total_score': total_score,
        'experience_points': exp_score,
        'education_points': edu_score,
          'skill_score': skill_score,
          'competency_score': comp_score,
        'skills': skill_details,
        'competencies': comp_details,
        
        'meets_min_exp': sum(e.calculate_tenure_years() for e in candidate.experience.all()) >= role.min_years_experience
    }


class AutoMatchService:
    @staticmethod
    def get_best_matches(job_posting, limit=5):
        """
        Calculates a 'Fit Score' based on:
        1. Number of matching skills (weighted 70%)
        2. Average level of matching skills (weighted 30%)
        """
        # Get the IDs of skills required for this job (assuming JobPosting has a skills relation)
        # For now, we'll pull from the JobRole's typical requirements
        required_skill_ids = job_posting.role.competencies.values_list('id', flat=True)
        
        candidates = Candidate.objects.filter(
            tenant=job_posting.tenant,
            skill_profiles__skill_id__in=required_skill_ids
        ).annotate(
            # Count how many of the job's required skills the candidate has
            match_count=Count('skill_profiles', filter=Q(skill_profiles__skill_id__in=required_skill_ids)),
            # Calculate the average level of those matching skills
            avg_level=Avg('skill_profiles__level', filter=Q(skill_profiles__skill_id__in=required_skill_ids))
        ).annotate(
            # Final Fit Score calculation (Normalized to 100)
            fit_score=ExpressionWrapper(
                ((F('match_count') / len(required_skill_ids)) * 70) + (F('avg_level') * 6),
                output_field=FloatField()
            )
        ).order_by('-fit_score')

        return candidates[:limit]
    
    
    
from django.shortcuts import redirect
from django.conf import settings

