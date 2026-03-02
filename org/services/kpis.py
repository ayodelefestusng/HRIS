from employees.models import Employee
from org.models import OrgUnit


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