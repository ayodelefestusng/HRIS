from django.utils import timezone
from employees.models import Employee
from leave.models import LeaveRequest
from payroll.models import PayrollEntry
from org.models import OrgUnit
from ats.models import Application
from ats.models import OnboardingPlan
from workflow.models import WorkflowInstance
from analytics.models import MetricSnapshot
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum, F
from payroll.models import PayrollPeriod, PayrollEntry
from django.db.models import Window, F
from django.db.models.functions import PercentRank
from performance .models import Appraisal, SuccessionProfile
import logging
logger = logging.getLogger(__name__)


def compute_headcount():
    return Employee.objects.filter(is_active=True).count()


def compute_turnover(days=365):
    cutoff = timezone.now().date() - timezone.timedelta(days=days)
    leavers = Employee.objects.filter(is_active=False, last_updated__gte=cutoff).count()
    population = Employee.objects.filter(last_updated__gte=cutoff).count() or 1
    return round((leavers / population) * 100, 2)


def compute_payroll_cost():
    latest_period = PayrollEntry.objects.order_by("-period__end_date").first()
    if not latest_period:
        return 0
    period = latest_period.period
    return PayrollEntry.objects.filter(period=period).aggregate(total=models.Sum("net_pay"))["total"] or 0


def compute_leave_usage(days=365):
    cutoff = timezone.now().date() - timezone.timedelta(days=days)
    return LeaveRequest.objects.filter(
        status="APP",
        start_date__gte=cutoff
    ).count()


def compute_ats_funnel():
    return {
        "new": Application.objects.filter(status="NEW").count(),
        "screening": Application.objects.filter(status="SCREENING").count(),
        "interview": Application.objects.filter(status="INTERVIEW").count(),
        "offer": Application.objects.filter(status="OFFER").count(),
        "hired": Application.objects.filter(status="HIRED").count(),
        "rejected": Application.objects.filter(status="REJECTED").count(),
    }


def compute_onboarding_progress():
    total = OnboardingPlan.objects.count()
    completed = OnboardingPlan.objects.filter(completed_at__isnull=False).count()
    return {
        "total": total,
        "completed": completed,
        "completion_rate": round((completed / total) * 100, 2) if total else 0,
    }


def compute_workflow_metrics():
    total = WorkflowInstance.objects.count()
    completed = WorkflowInstance.objects.filter(completed_at__isnull=False).count()
    return {
        "total": total,
        "completed": completed,
        "completion_rate": round((completed / total) * 100, 2) if total else 0,
    }


def compute_org_kpis():
    data = {}
    for unit in OrgUnit.objects.all():
        headcount = Employee.objects.filter(
            job_history__department__org_unit__path__startswith=unit.path,
            job_history__is_active=True,
        ).distinct().count()

        data[unit.code] = {
            "name": unit.name,
            "headcount": headcount,
            "budget": float(unit.budget),
            "headcount_limit": unit.headcount_limit,
        }
    return data


def compute_all_metrics():
    return {
        "headcount": compute_headcount(),
        "turnover_rate": compute_turnover(),
        "payroll_cost": compute_payroll_cost(),
        "leave_usage": compute_leave_usage(),
        "ats_funnel": compute_ats_funnel(),
        "onboarding": compute_onboarding_progress(),
        "workflow": compute_workflow_metrics(),
        "org_kpis": compute_org_kpis(),
    }


def create_snapshot():
    metrics = compute_all_metrics()
    snap = MetricSnapshot.objects.create(metrics=metrics)
    return snap



from django.db.models import Count
from employees.models import Employee, Department, CompensationRecord
from django.utils import timezone
from datetime import timedelta


def headcount_for_department(department: Department) -> int:
    return (
        Employee.objects.filter(
            job_history__department=department,
            job_history__is_active=True,
        )
        .distinct()
        .count()
    )


def average_salary() -> float:
    """
    Very basic average using latest CompensationRecord per employee.
    Can be improved to be more efficient later.
    """
    employees = Employee.objects.all()
    salaries = []

    for emp in employees:
        latest = CompensationRecord.objects.filter(employee=emp).order_by("-effective_date").first()
        if latest:
            salaries.append(float(latest.salary_amount))

    if not salaries:
        return 0.0
    return sum(salaries) / len(salaries)


def turnover_rate(days: int = 365) -> float:
    """
    Simple turnover: inactive employees in last `days` / active + inactive in that window.
    """
    cutoff = timezone.now().date() - timedelta(days=days)

    leavers = Employee.objects.filter(is_active=False, last_updated__gte=cutoff).count()
    population = Employee.objects.filter(last_updated__gte=cutoff).count() or 1

    return round((leavers / population) * 100, 2)


from django.db.models import Count
from employees.models import Employee

def headcount_for_unit(unit):
    return Employee.objects.filter(
        job_history__department__org_unit__path__startswith=unit.path,
        job_history__is_active=True
    ).distinct().count()


from org.models  import OrgUnit, OrgUnitVersion, OrgWorkflowRoute
from org.serializers import OrgUnitSerializer

def create_org_version():
    from org.models import OrgUnit
    tree = OrgUnitSerializer(OrgUnit.objects.filter(parent__isnull=True), many=True).data

    last_version = OrgUnitVersion.objects.first()
    next_version = (last_version.version + 1) if last_version else 1

    OrgUnitVersion.objects.create(
        version=next_version,
        data=tree
    )
        
           



    
    
def compute_org_metrics():
    from org.models import OrgUnit
    from employees.models import Employee

    metrics = {}

    for unit in OrgUnit.objects.all():
        headcount = Employee.objects.filter(
            job_history__department__org_unit__path__startswith=unit.path,
            job_history__is_active=True
        ).distinct().count()

        metrics[unit.code] = {
            "headcount": headcount,
            "budget": float(unit.budget),
            "headcount_limit": unit.headcount_limit,
            "cost_center": unit.cost_center,
        }

    return metrics
## Usage emaplve
def get_approvers_for_employee(employee):
    unit = employee.org_unit
    routes = OrgWorkflowRoute.objects.filter(org_unit=unit)

    approvers = []
    for route in routes:
        approvers.extend(
            Employee.objects.filter(roles__role__name=route.approver_role)
        )
    return approvers


def merge_org_units(source_unit, target_unit):
    # Move employees
    source_unit.employees.update(org_unit=target_unit)

    # Move children
    for child in source_unit.children.all():
        child.parent = target_unit
        child.save()

    # Delete or archive source
    source_unit.delete()
    
    
def split_org_unit(unit, new_units_data):
    """
    new_units_data = [
        {"name": "New A", "employees": [1,2,3]},
        {"name": "New B", "employees": [4,5]},
    ]
    """
    for data in new_units_data:
        new_unit = OrgUnit.objects.create(
            name=data["name"],
            parent=unit.parent
        )
        Employee.objects.filter(id__in=data["employees"]).update(org_unit=new_unit)
        
        
def reorder_org_units(parent, ordered_ids):
    for index, unit_id in enumerate(ordered_ids):
        OrgUnit.objects.filter(id=unit_id, parent=parent).update(sort_order=index)
        
        
def move_org_unit(unit_id, new_parent_id):
    unit = OrgUnit.objects.get(id=unit_id)
    new_parent = OrgUnit.objects.get(id=new_parent_id)

    unit.parent = new_parent
    unit.save()
    
    
from django.db.models import Count
from employees.models import Employee

def headcount_for_unit(unit):
    return Employee.objects.filter(
        job_history__department__org_unit__path__startswith=unit.path,
        job_history__is_active=True
    ).distinct().count()


from org.models  import OrgUnit, OrgUnitVersion, OrgWorkflowRoute
from org.serializers import OrgUnitSerializer

def create_org_version():
    from org.models import OrgUnit
    tree = OrgUnitSerializer(OrgUnit.objects.filter(parent__isnull=True), many=True).data

    last_version = OrgUnitVersion.objects.first()
    next_version = (last_version.version + 1) if last_version else 1

    OrgUnitVersion.objects.create(
        version=next_version,
        data=tree
    )
        
           



    
    
def compute_org_metrics():
    from org.models import OrgUnit
    from employees.models import Employee

    metrics = {}

    for unit in OrgUnit.objects.all():
        headcount = Employee.objects.filter(
            job_history__department__org_unit__path__startswith=unit.path,
            job_history__is_active=True
        ).distinct().count()

        metrics[unit.code] = {
            "headcount": headcount,
            "budget": float(unit.budget),
            "headcount_limit": unit.headcount_limit,
            "cost_center": unit.cost_center,
        }

    return metrics
## Usage emaplve
def get_approvers_for_employee(employee):
    unit = employee.org_unit
    routes = OrgWorkflowRoute.objects.filter(org_unit=unit)

    approvers = []
    for route in routes:
        approvers.extend(
            Employee.objects.filter(roles__role__name=route.approver_role)
        )
    return approvers


def merge_org_units(source_unit, target_unit):
    # Move employees
    source_unit.employees.update(org_unit=target_unit)

    # Move children
    for child in source_unit.children.all():
        child.parent = target_unit
        child.save()

    # Delete or archive source
    source_unit.delete()
    
    
def split_org_unit(unit, new_units_data):
    """
    new_units_data = [
        {"name": "New A", "employees": [1,2,3]},
        {"name": "New B", "employees": [4,5]},
    ]
    """
    for data in new_units_data:
        new_unit = OrgUnit.objects.create(
            name=data["name"],
            parent=unit.parent
        )
        Employee.objects.filter(id__in=data["employees"]).update(org_unit=new_unit)
        
        
def reorder_org_units(parent, ordered_ids):
    for index, unit_id in enumerate(ordered_ids):
        OrgUnit.objects.filter(id=unit_id, parent=parent).update(sort_order=index)
        
        
def move_org_unit(unit_id, new_parent_id):
    unit = OrgUnit.objects.get(id=unit_id)
    new_parent = OrgUnit.objects.get(id=new_parent_id)

    unit.parent = new_parent
    unit.save()

class PayrollAnalyticsService:
    
    def __init__(self, tenant):
        self.tenant = tenant

    def get_variance_report(self, current_period):
        
   
        """
        Compares current period entries against the previous month.
        """
        # 1. Identify the previous closed period
        previous_period = PayrollPeriod.objects.filter(
            tenant=self.tenant,
            status="CLO",
            end_date__lt=current_period.start_date
        ).order_by('-end_date').first()

        report = {
            'period_name': current_period.name,
            'previous_period_name': previous_period.name if previous_period else "N/A",
            'metrics': [],
            'totals': {
                'current_gross': Decimal('0.00'),
                'previous_gross': Decimal('0.00'),
                'variance_amount': Decimal('0.00'),
                'variance_percentage': Decimal('0.00'),
            }
        }

        # 2. Get all entries for current period
        current_entries = PayrollEntry.objects.filter(period=current_period, tenant=self.tenant)
        
        for entry in current_entries:
            # Find the same employee in the previous period
            prev_entry = None
            if previous_period:
                prev_entry = PayrollEntry.objects.filter(
                    employee=entry.employee, 
                    period=previous_period
                ).first()

            prev_net = prev_entry.net_salary if prev_entry else Decimal('0.00')
            variance = entry.net_salary - prev_net
            
            # Calculate % change
            percent_change = 0
            if prev_net > 0:
                percent_change = (variance / prev_net) * 100

            report['metrics'].append({
                'employee': entry.employee.full_name,
                'current_net': entry.net_salary,
                'previous_net': prev_net,
                'variance': variance,
                'percent_change': round(percent_change, 2),
                'flag': abs(percent_change) > 10 # Flag if change > 10%
            })

        # 3. Calculate Global Totals
        report['totals']['current_gross'] = current_entries.aggregate(Sum('gross_salary'))['gross_salary__sum'] or 0
        if previous_period:
            report['totals']['previous_gross'] = PayrollEntry.objects.filter(
                period=previous_period
            ).aggregate(Sum('gross_salary'))['gross_salary__sum'] or 0
            
            report['totals']['variance_amount'] = report['totals']['current_gross'] - report['totals']['previous_gross']
            if report['totals']['previous_gross'] > 0:
                report['totals']['variance_percentage'] = round(
                    (report['totals']['variance_amount'] / report['totals']['previous_gross']) * 100, 2
                )

        return report
    
    

def get_high_potentials(tenant, cycle_id):
    """
    Identifies the top 10% of performers for a specific tenant and cycle.
    Uses Database Window functions for high performance.
    """
    # 1. Get all completed appraisals for the tenant cycle
    queryset = Appraisal.objects.filter(
        tenant=tenant,
        cycle_id=cycle_id,
        status='COMPLETED'
    ).annotate(
        # Calculate the percentile rank of the final_score
        percentile=Window(
            expression=PercentRank(),
            order_by=F('final_score').asc(),
        )
    )

    # 2. Filter the top 10% (Percentile > 0.9)
    hipos = [a for a in queryset if a.percentile >= 0.9]
    
    logger.info(f"[REPORT] High Potential Identification run for Tenant: {tenant.code}. Found: {len(hipos)}")
    return hipos



from django.db.models import Avg

class FeedbackAnalyticsService:
    def __init__(self, tenant):
        self.tenant = tenant

    def get_360_summary(self, employee, cycle):
        
        from performance.models import FeedbackRequest, FeedbackResponse
        """
        Aggregates feedback by relationship type to protect anonymity.
        Only shows results if there are at least 3 respondents in a category (HR Best Practice).
        """
        results = FeedbackResponse.objects.filter(
            request__subject=employee,
            request__cycle=cycle,
            tenant=self.tenant
        )
        
        summary = {}
        for rel_code, rel_name in FeedbackRequest.RELATIONSHIP_CHOICES:
            rel_data = results.filter(request__relationship=rel_code)
            count = rel_data.count()
            
            # Privacy Guard: If fewer than 3 peers responded, group them into 'Others' 
            # to prevent the subject from guessing who said what.
            if count >= 3:
                summary[rel_name] = {
                    "avg_rating": rel_data.aggregate(Avg('average_rating'))['average_rating__avg'],
                    "count": count
                }
            else:
                summary[f"{rel_name} (Insufficient Data)"] = "Data hidden for anonymity"
                
        return summary
    
    
class SuccessionService:
    def __init__(self, tenant):
        self.tenant = tenant

    def get_talent_matrix(self):
        profiles = SuccessionProfile.objects.filter(tenant=self.tenant).select_related('employee')
        matrix = { (x, y): [] for x in range(1, 4) for y in range(1, 4) }
        
        for profile in profiles:
            coord = profile.get_9_box_coordinate()
            matrix[coord].append(profile)
            
        logger.info(f"[SUCCESSION_ANALYTICS] Generated 9-Box Matrix for Tenant: {self.tenant.id}")
        return matrix