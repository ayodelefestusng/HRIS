from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from leave.models import LeaveBalance, LeaveType, PublicHoliday, LeaveRequest
from employees.models import Employee
from notifications.services.notification_sender import create_notification
import logging

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# APPROVE LEAVE
# ----------------------------------------------------------------------
def approve_leave(leave_request, approver):
    """
    Approves a leave request, deducts balance, and sends notification.
    """
    try:
        leave_request.status = "APP"
        leave_request.approved_by = approver
        leave_request.decided_at = timezone.now()
        leave_request.save()

        # Deduct leave balance
        balance = LeaveBalance.objects.get(
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            year=timezone.now().year,
        )
        balance.balance_days -= leave_request.duration_days
        balance.save()

        # Notification
        create_notification(
            recipient=leave_request.employee.user,
            title="Leave Request Approved",
            message=(
                f"Your {leave_request.leave_type.name} request "
                f"from {leave_request.start_date} to {leave_request.end_date} "
                f"has been approved."
            ),
            target=leave_request,
            send_email=True,
        )

        return leave_request
    except Exception as e:
        logger.error(
            f"Error approving leave request {leave_request.id}: {e}", exc_info=True
        )
        raise


# ----------------------------------------------------------------------
# REJECT LEAVE
# ----------------------------------------------------------------------
def reject_leave(leave_request, approver):
    """
    Rejects a leave request and sends notification.
    """
    try:
        leave_request.status = "REJ"
        leave_request.approved_by = approver
        leave_request.decided_at = timezone.now()
        leave_request.save()

        create_notification(
            recipient=leave_request.employee.user,
            title="Leave Request Rejected",
            message=(
                f"Your {leave_request.leave_type.name} request "
                f"from {leave_request.start_date} to {leave_request.end_date} "
                f"was rejected."
            ),
            target=leave_request,
            send_email=True,
        )

        return leave_request
    except Exception as e:
        logger.error(
            f"Error rejecting leave request {leave_request.id}: {e}", exc_info=True
        )
        raise


# ----------------------------------------------------------------------
# WORKING DAYS CALCULATION
# ----------------------------------------------------------------------
def get_working_days(start_date, end_date, exclude_weekends=True):
    """
    Counts working days between start_date and end_date inclusive.
    Excludes weekends and public holidays.
    """
    try:
        if start_date > end_date:
            return 0

        holidays = set(
            PublicHoliday.objects.filter(
                date__gte=start_date, date__lte=end_date
            ).values_list("date", flat=True)
        )

        current = start_date
        count = 0

        while current <= end_date:
            is_weekend = current.weekday() >= 5
            is_holiday = current in holidays

            if not (exclude_weekends and is_weekend) and not is_holiday:
                count += 1

            current += timedelta(days=1)

        return count
    except Exception as e:
        logger.error(f"Error calculating working days: {e}", exc_info=True)
        return 0


# ----------------------------------------------------------------------
# ANNUAL LEAVE ACCRUAL
# ----------------------------------------------------------------------
def accrue_annual_leave_for_year(year=None):
    """
    Allocates annual leave to all active employees for all leave types.
    """
    try:
        if year is None:
            year = timezone.now().year

        employees = Employee.objects.filter(is_active=True)
        leave_types = LeaveType.objects.all()

        for emp in employees:
            for lt in leave_types:
                allocation = lt.annual_allocation_days or Decimal("0")

                balance, created = LeaveBalance.objects.get_or_create(
                    employee=emp,
                    leave_type=lt,
                    year=year,
                    defaults={"balance_days": allocation},
                )

                if not created:
                    balance.balance_days += allocation
                    balance.save()
    except Exception as e:
        logger.error(f"Error accruing leave for year {year}: {e}", exc_info=True)
        raise


# ----------------------------------------------------------------------
# CARRY OVER LEAVE
# ----------------------------------------------------------------------
def carry_over_leave_balances(from_year=None, to_year=None, max_carry_over_days=10):
    """
    Carries over unused leave from one year to the next.
    """
    try:
        if to_year is None:
            to_year = timezone.now().year
        if from_year is None:
            from_year = to_year - 1

        balances = LeaveBalance.objects.filter(year=from_year)

        for bal in balances:
            carry = min(bal.balance_days, max_carry_over_days)

            target, created = LeaveBalance.objects.get_or_create(
                employee=bal.employee,
                leave_type=bal.leave_type,
                year=to_year,
                defaults={"balance_days": carry},
            )

            if not created:
                target.balance_days += carry
                target.save()
    except Exception as e:
        logger.error(f"Error carrying over leave balances: {e}", exc_info=True)
        raise
