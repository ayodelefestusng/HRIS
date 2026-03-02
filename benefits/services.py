from employees.models import Employee
from .models import Invoice

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