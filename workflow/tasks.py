from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from workflow.models import WorkflowInstance
from workflow.services.workflow_service import WorkflowService
import logging

from celery import shared_task
from django.utils import timezone
from employees.models import Employee, ExitProcess
import logging

from payroll.models import PayrollPeriod, Payslip
from notifications.models import Notification
from workflow.services.workflow_service import _send_notification_email,create_org_version,generate_snapshot
logger = logging.getLogger(__name__)



from celery import shared_task
from django.utils import timezone
from leave.models import LeaveRequest
from leave.services.leave_services import (
    accrue_annual_leave_for_year,
    carry_over_leave_balances,
)
# tasks.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import WorkflowInstance, Delegation, Opportunity, ProcurementRequest
from org.views import log_with_context

logger = logging.getLogger(__name__)


@shared_task
def auto_close_stale_workflows():
    qs = WorkflowInstance.objects.filter(
        completed_at__isnull=True, current_step__isnull=True
    )
    count = qs.update(completed_at=timezone.now())
    return f"Closed {count} stale workflows"
from celery import shared_task
from .services import WorkflowService
import logging

logger = logging.getLogger(__name__)

@shared_task(name="tasks.run_workflow_escalations")
def run_workflow_escalations():
    """
    Background task to escalate overdue workflow requests.
    """
    logger.info("Starting Batch Workflow Escalation Check...")
    try:
        # We initialize without a specific tenant if your logic 
        # needs to loop through all tenants, or pass a default.
        service = WorkflowService() 
        service.process_escalations()
        return "Escalation check completed successfully."
    except Exception as e:
        logger.error(f"Escalation task failed: {str(e)}")
        return f"Error: {str(e)}"

@shared_task
def send_workflow_nag_emails():
    """
    Scans pending workflows and emails managers who exceed TurnaroundTime.
    CCs the manager's line manager for escalation.
    """
    # 1. Get all incomplete workflow instances
    pending_items = WorkflowInstance.objects.filter(completed_at__isnull=True)

    for instance in pending_items:
        try:
            stage = instance.current_stage
            if not stage or not stage.turnaround_time:
                continue

            # 2. Calculate if the "Nag" threshold is met
            deadline = instance.created_at + timezone.timedelta(
                hours=stage.turnaround_time
            )

            if timezone.now() > deadline:
                # 3. Identify the current approver (Manager)
                service = WorkflowService(tenant=instance.tenant)
                manager = service.get_approver(instance, stage)

                if manager and manager.email:
                    line_manager = manager.line_manager
                    cc_list = (
                        [line_manager.email]
                        if line_manager and line_manager.email
                        else []
                    )

                    # 4. Fire the "Nag" Email
                    subject = f"URGENT: Pending Approval for {instance.workflow.name} - {instance.approval_ref}"
                    message = (
                        f"Dear {manager.first_name},\n\n"
                        f"The request {instance.approval_ref} initiated by {instance.initiated_by.full_name} "
                        f"has exceeded the expected turnaround time of {stage.turnaround_time} hours.\n"
                        f"Please log in to the HR Portal to take action."
                    )

                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[manager.email],
                        cc_list=cc_list,
                        fail_silently=True,
                    )
        except Exception as e:
            logger.error(f"Error processing nag email for {instance.id}: {e}")
            continue
    return "Nag emails processed"



@shared_task
def deactivate_inactive_employees():
    """
    Example HR task: deactivate employees flagged as deleted.
    """
    qs = Employee.objects.filter(is_deleted=True, is_active=True)
    count = qs.update(is_active=False, last_updated=timezone.now())
    return f"Deactivated {count} employees"


@shared_task
def process_scheduled_exits():
    """Daily task to deactivate employees on their Last Working Day."""
    today = timezone.now().date()
    exiting_today = ExitProcess.objects.filter(
        last_working_day__lte=today, status__ne="EXITED"
    ).select_related("employee")

    count = 0
    for exit_p in exiting_today:
        # 1. Deactivate User Account
        user = exit_p.employee.user
        if user:
            user.is_active = False
            user.save()

        # 2. Update Employee Status
        exit_p.employee.status = "TERMINATED"
        exit_p.employee.save()

        # 3. Close Exit Process
        exit_p.status = "EXITED"
        exit_p.save()

        count += 1
        logger.info(
            f"[SECURITY] Access revoked for {exit_p.employee.full_name} on LWD."
        )

    return f"Successfully exited {count} employees today."

@shared_task
def auto_cancel_expired_pending_requests():
    today = timezone.now().date()
    qs = LeaveRequest.objects.filter(status="PEN", start_date__lt=today)
    count = qs.update(status="CAN", decided_at=timezone.now())
    return f"Auto-cancelled {count} expired leave requests"


@shared_task
def run_annual_leave_accrual(year=None):
    if year is None:
        year = timezone.now().year
    accrue_annual_leave_for_year(year)
    return f"Leave accrual completed for year {year}"



@shared_task(name="workflow.nag_engine")
def run_nag_engine():
    """
    Identifies overdue stages and sends notifications/alerts.
    """
    # Find all instances that are not completed
    pending_instances = WorkflowInstance.objects.filter(completed_at__isnull=True)
    
    for instance in pending_instances:
        try:
            stage = instance.current_stage
            # Calculate when this stage was entered (from the last action or creation)
            last_action = instance.actions.order_by('-created_at').first()
            start_time = last_action.created_at if last_action else instance.created_at
            
            overdue_threshold = start_time + timedelta(hours=stage.turnaround_time)
            
            if timezone.now() > overdue_threshold:
                approvers = instance.resolve_current_approvers()
                
                for approver in approvers:
                    log_with_context(logging.WARNING, 
                        f"NAG: Stage {stage.sequence} overdue for {instance.approval_ref}", 
                        approver.user
                    )
                    # Here you would trigger: send_email_notification(approver, instance)
                    
        except Exception as e:
            logger.error(f"Nag Engine error on Instance {instance.id}: {str(e)}", exc_info=True)
@shared_task
def run_leave_carry_over(from_year=None, to_year=None, max_carry_over_days=10):
    carry_over_leave_balances(from_year, to_year, max_carry_over_days)
    return f"Leave carry-over completed from {from_year} to {to_year}"


@shared_task
def send_pending_email_notifications():
    qs = Notification.objects.filter(send_email=True, recipient__email__isnull=False)
    count = 0
    for n in qs:
        _send_notification_email(n)
        count += 1
    return f"Processed {count} notification emails"

@shared_task
def remind_pending_onboarding_tasks():
    count = 0
    for plan in OnboardingPlan.objects.filter(completed_at__isnull=True):
        pending = plan.tasks.filter(status="PENDING")
        if pending.exists():
            count += 1
            # You can send reminders here
    return f"Checked {count} onboarding plans"


@shared_task
def nightly_org_versioning():
    version = create_org_version()
    return f"Org version {version} created"


@shared_task
def nightly_org_snapshot():
    snap = generate_snapshot()
    return f"Snapshot {snap.id} created"



@shared_task
def run_payroll(period_id):
    period = PayrollPeriod.objects.get(id=period_id)
    period.status = "OPN"
    period.save()

    compute_payroll_for_period(period)

    return f"Payroll processed for period {period.name}"


@shared_task
def task_send_bulk_payslips(payslip_ids, period):
    current_period = PayrollPeriod.objects.get(name=period)
    service = PayrollService(period=current_period)
    payslips = Payslip.objects.filter(id__in=payslip_ids)

    for payslip in payslips:
        try:
            service.send_employee_payslip_email(payslip)
        except Exception as e:
            # Log specific email failure but continue with others
            logger.error(f"Failed to send to {payslip.employee.first_name}: {e}")
            pass


@shared_task
def audit_payroll_readiness():
    """Checks for Active employees with no payroll records for the current month."""
    today = timezone.now()
    active_no_pay = Employee.objects.filter(
        status="ACTIVE",
    ).exclude(
        payroll_entries__month__year=today.year,
        payroll_entries__month__month=today.month,
    )  # Improved logic if possible but using filter as per requirement

    # Original logic in snippet was: payroll_entries__month__month__ne=today.month
    # Django ORM exclude is safer for 'not equal' or logic

    for emp in active_no_pay:
        logger.error(
            f"[PAYROLL_GAP] Alert: {emp.first_name} {emp.last_name} is Active but missing from {today.strftime('%B')} payroll cycle."
        )

@shared_task
def sync_away_status_and_delegations():
    """
    1. Synchronizes employee 'away' status based on active LeaveRequests.
    2. Terminates delegations for employees who are no longer 'away'.
    3. Auto-creates delegations for approved leave requests that are starting today.
    """
    today = timezone.now().date()
    
    # 1. Update 'away' status based on approved leave
    EmployeesOnLeave = Employee.objects.filter(
        leave_requests__approval_status='approved',
        leave_requests__start_date__lte=today,
        leave_requests__end_date__gte=today
    ).distinct()
    
    for emp in EmployeesOnLeave:
        if not emp.away or emp.work_status != 'L':
            emp.away = True
            emp.work_status = 'L'
            emp.save()

    # 2. Reset 'away' status for those whose leave ended yesterday
    yesterday = today - timedelta(days=1)
    EmployeesBackFromLeave = Employee.objects.filter(
        away=True,
        work_status='L'
    ).exclude(
        leave_requests__approval_status='approved',
        leave_requests__start_date__lte=today,
        leave_requests__end_date__gte=today
    )
    
    for emp in EmployeesBackFromLeave:
        emp.away = False
        emp.work_status = 'A' # Active
        emp.save()
        
        # Auto-terminate delegations given by this employee since they are back
        Delegation.objects.filter(delegator=emp, is_active=True).update(is_active=False)

    # 3. Auto-create delegations for leave starting today
    NewLeaves = LeaveRequest.objects.filter(
        approval_status='approved',
        start_date=today,
        relief_employee__isnull=False
    )
    
    for leave in NewLeaves:
        # Check if delegation already exists
        exists = Delegation.objects.filter(
            delegator=leave.employee,
            delegatee=leave.relief_employee,
            start_date=leave.start_date,
            end_date=leave.end_date,
            is_active=True
        ).exists()
        
        if not exists:
            Delegation.objects.create(
                tenant=leave.tenant,
                delegator=leave.employee,
                delegatee=leave.relief_employee,
                start_date=leave.start_date,
                end_date=leave.end_date,
                reason=f"Auto-delegation for leave: {leave.leave_type.name}",
                is_active=True
            )
            
@shared_task
def check_crm_stale_opportunities():
    """
    Scans for opportunities that haven't been updated in 7 days.
    """
    threshold = timezone.now() - timedelta(days=7)
    stale_opps = Opportunity.objects.filter(
        updated_at__lt=threshold
    ).exclude(stage__in=['closed_won', 'closed_lost'])
    
    count = 0
    for opp in stale_opps:
        if opp.owner and opp.owner.email:
            send_mail(
                subject=f"STALE OPPORTUNITY: {opp.name}",
                message=f"Hi {opp.owner.first_name},\n\nOpportunity '{opp.name}' has not been updated in over 7 days. Please check the pipeline.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[opp.owner.email],
                fail_silently=True
            )
            count += 1
    return f"Notified owners of {count} stale opportunities"

@shared_task
def check_procurement_deadlines():
    """
    Scans for pending procurement requests older than 48 hours.
    """
    threshold = timezone.now() - timedelta(hours=48)
    pending_reqs = ProcurementRequest.objects.filter(
        status='pending',
        created_at__lt=threshold
    )
    
    count = 0
    for req in pending_reqs:
        # Notify the procurement officer or admin
        logger.warning(f"DELAYED PROCUREMENT: Request '{req.subject}' is pending for over 48 hours.")
        count += 1
    return f"Logged alerts for {count} delayed procurement requests"
