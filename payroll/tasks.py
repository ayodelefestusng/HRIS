from celery import shared_task
from django.utils import timezone
import logging
from payroll.models import PayrollPeriod, Payslip

from workflow.services.workflow_service import PayrollService,compute_payroll_for_period
from employees.models import Employee

logger = logging.getLogger(__name__)


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
