from itertools import cycle
from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone
from employees.models import Employee

from org.models import TenantModel, tenant_directory_path

from django.db import models

class GradeNonFinancialBenefit(models.Model):
    """
    Car entitlement linked to a grade.
    Example: Level 10 → Honda Accord, Level 11 → BMW.
    """
    grade = models.ForeignKey("org.Grade", on_delete=models.CASCADE, related_name="car_benefits")
    Housing = models.CharField(max_length=150)
    other = models.CharField(max_length=150)
    def __str__(self):
        return f"{self.grade.name} → {self.Housing}" 

class GradeHealthInsurance(models.Model):
    """
    Represents a health insurance plan tied to a grade.
    Example: All Level 10 employees → AXA Mansard, Policy X.
    """
    grade = models.ForeignKey("org.Grade", on_delete=models.CASCADE, related_name="health_insurances")
    provider = models.CharField(max_length=200)
    policy_number = models.CharField(max_length=100, unique=True)
    coverage_details = models.TextField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.grade.name} - {self.provider} ({self.policy_number})"

 
# class GradeMonthlyAllowance(models.Model):
#     """
#     Car entitlement linked to a grade.
#     Example: Level 10 → Honda Accord, Level 11 → BMW.
#     """
#     grade = models.ForeignKey("org.Grade", on_delete=models.CASCADE, related_name="car_benefits")
#     housing = models.PositiveIntegerField(max_length=150)
#     transport = models.PositiveIntegerField(max_length=150)

#     def __str__(self):
#         return f"{self.grade.name} → {self.housing}"

   
# class GradeOtherAllowance(models.Model):
#     """
#     Represents allowances tied to a grade.
#     Example: Level 5 → Phone Bill 10k, Level 6 → Phone Bill 11k.
#     """
#     grade = models.ForeignKey("org.Grade", on_delete=models.CASCADE, related_name="grade_allowances")
#     type = models.CharField(max_length=100)  # e.g. Housing, Transport, Phone Bill
#     description = models.TextField(blank=True)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     recurring = models.BooleanField(default=True)
#     cycle = models.IntegerField(default=0, help_text="Number of months between recurring payments. 0 for one-time.")

#     def __str__(self):
#         return f"{self.grade.name} - {self.type} ({self.amount})"

# CYCLE_CHOICES = [
#         ("M", "Monthly"),
#         ("BM", "Bi-Monthly"),
#         ("Q", "Quarterly"),
#         ("H", "Half-Yearly"),
#         ("Y", "Yearly")
#     ]
# class OtherAllowance(models.Model):
#     """
#     Represents allowances tied to a grade.
#     Example: Level 5 → Phone Bill 10k, Level 6 → Phone Bill 11k.
#     """
    
#     type = models.CharField(max_length=100)  # e.g. Housing, Transport, Phone Bill
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     description = models.TextField(blank=True)
#     recurring = models.BooleanField(default=True)
#     cycle = models.CharField(max_length=3, choices=CYCLE_CHOICES, default="M")


#     def __str__(self):
#         return f" - {self.type} ({self.amount}) {self.cycle}"
    

# class EmployeePay(models.Model):
#     employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employee_pays")
#     allowance = models.ForeignKey(OtherAllowance, on_delete=models.CASCADE, related_name="employee_pays")
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     start_date = models.DateField()
#     end_date = models.DateField(null=True, blank=True)
#     active = models.BooleanField(default=True)



class Reimbursement(models.Model):
    """
    Represents expense reimbursements requested by employees.
    Examples: travel expenses, medical claims.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="benefits_reimbursements")
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    request_date = models.DateField(default=timezone.now)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="benefits_approved_reimbursements")
    processed_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee} - {self.amount} ({'Approved' if self.approved else 'Pending'})"