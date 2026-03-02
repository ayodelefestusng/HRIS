from employees.models import Employee
from .models import Invoice


from django.db.models import Q
from employees.models import Employee
from ats.models import Candidate
from employees.models import ExitProcess

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

class BillingEngine:
    @staticmethod
    def calculate_monthly_bill(tenant):
        plan = tenant.subscription_plan # Assume tenant has a ForeignKey to Plan
        active_count = Employee.objects.filter(tenant=tenant, status='ACTIVE').count()
        
        # Calculation: Base Price + (Active Employees * Price Per Head)
        total_amount = plan.base_price + (active_count * plan.per_employee_cost)
        
        return {
            'headcount': active_count,
            'total': total_amount,
            'plan_name': plan.name
        }