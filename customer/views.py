from django.shortcuts import render

# Create your views here.
from .models import (

    Opportunity, Account, Contact
)

class CRMPipelineView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/crm_pipeline.html"

    def post(self, request, *args, **kwargs):
        action = request.GET.get('action')
        if action == 'move':
            opp_id = request.GET.get('id')
            to_stage = request.GET.get('to')
            try:
                opp = Opportunity.objects.get(pk=opp_id, tenant=request.user.tenant)
                # Instead of immediate update, trigger workflow
                opp.trigger_stage_transition(to_stage, request.user)
            except Opportunity.DoesNotExist:
                pass
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, 'tenant', None)
        
        # Group opportunities by stage
        stages = [choice[0] for choice in Opportunity.SALES_STAGE_CHOICES]
        pipeline = {stage: [] for stage in stages}
        
        opportunities = Opportunity.objects.filter(tenant=tenant).select_related('account', 'owner')
        for opp in opportunities:
            if opp.stage in pipeline:
                pipeline[opp.stage].append(opp)
        
        context['pipeline'] = pipeline
        context['stage_choices'] = Opportunity.SALES_STAGE_CHOICES
        return context




class Customer(models.Model):
    customer_id = models.CharField(max_length=20, unique=True)
    first_name = models.ForeignKey("NigerianName", on_delete=models.SET_NULL, null=True, related_name="first_names")
    last_name = models.ForeignKey("NigerianName", on_delete=models.SET_NULL, null=True, related_name="last_names")
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=11, unique=True)
    account_number = models.CharField(max_length=10, unique=True)

    gender = models.CharField(max_length=10, choices=[("male", "Male"), ("female", "Female")])
    city_of_residence = models.CharField(max_length=100)
    state_of_residence = models.CharField(max_length=100)
    nationality = models.CharField(max_length=50, default="Nigeria")
    occupation = models.CharField(max_length=100)
    date_of_birth = models.DateField()

    branch = models.ForeignKey("Branch", on_delete=models.SET_NULL, null=True)  # Customer's registered branch

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.account_number}"

    def clean(self):
        """Custom validation for phone numbers and account numbers."""
        if not self.phone_number.startswith("0") or self.phone_number[1] not in "6789":
            raise ValueError("Phone number must start with '0' and second digit must be between 6 and 9.")
        if len(self.account_number) != 10 or not self.account_number.isdigit():
            raise ValueError("Account number must be exactly 10 digits.")

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("deposit", "Deposit"),
        ("withdrawal", "Withdrawal"),
        ("transfer", "Transfer"),
        ("airtime", "Airtime Purchase"),
        ("loan", "Loan Disbursement"),
        ("bill_payment", "Bill Payment"),
        ("balance_enquiry", "Balance Enquiry"),
    ]

    TRANSACTION_CHANNELS = [
        ("atm", "ATM"),
        ("pos", "POS"),
        ("branch", "Branch"),
        ("web", "Web"),
        ("mobile", "Mobile"),
    ]

    transaction_id = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    transaction_channel = models.CharField(max_length=10, choices=TRANSACTION_CHANNELS)
    timestamp = models.DateTimeField(auto_now_add=False)
    def __str__(self):
        return f"{self.transaction_type} via {self.transaction_channel} - {self.amount}"


class LoanReport(models.Model):
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)
    loan_account_number = models.CharField(max_length=20, unique=True)
    amount_collected = models.DecimalField(max_digits=12, decimal_places=2)
    date_loan_booked = models.DateField()
    last_repayment_date = models.DateField(null=True, blank=True)
    loan_balance = models.DecimalField(max_digits=12, decimal_places=2)

    branch_booked = models.ForeignKey("Branch", on_delete=models.SET_NULL, null=True)  # Branch where loan was processed

    def __str__(self):
        return f"Loan {self.loan_account_number} - Balance: {self.loan_balance}"


class ComplianceRecord(models.Model):
    record_id = models.CharField(max_length=30, unique=True)
    transaction = models.ForeignKey("Transaction", on_delete=models.CASCADE)
    compliance_status = models.CharField(max_length=50, choices=[("passed", "Passed"), ("flagged", "Flagged")])
    audit_notes = models.TextField(blank=True)
    checked_by = models.CharField(max_length=255)
    checked_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Compliance {self.record_id} - {self.compliance_status}"
    
class BranchPerformance(models.Model):
    branch = models.ForeignKey("Branch", on_delete=models.CASCADE)
    total_customers = models.PositiveIntegerField()
    total_transactions = models.PositiveIntegerField()
    revenue_generated = models.DecimalField(max_digits=12, decimal_places=2)
    report_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.branch.branch_name} - {self.report_date}"                    
    

