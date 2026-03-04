from datetime import datetime
from xml.dom.minidom import Text

from django.db import models
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
# from .models import Opportunity, Account, Contact
from django.core.exceptions import ValidationError
from regex import T
from sqlalchemy import Column, Integer, String
from org.models import Location   
# Create your models here.
# crm_core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser # If you want to extend User directly
# sales/models.py
from django.db import models
from django.conf import settings # To get AUTH_USER_MODEL
# from crm_core.models import Account, Contact # Assuming these are in crm_core
# crm_core/models.py (continued)
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
# If you prefer a separate profile linked to User:
from django.conf import settings # To get AUTH_USER_MODEL
from core.models import TenantModel
from django.utils import log, timezone
from workflow.models import WorkflowCompatibleModel
from org.views import log_with_context
import logging
logger = logging.getLogger(__name__)
# Extending Django's User model for CRM-specific fields
class CRMUser(TenantModel):
    # Add CRM-specific fields here, e.g.
    title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    phone_extension = models.CharField(max_length=100, blank=True)
    is_sales_manager = models.BooleanField(default=False)

    # You could add a 'territory' field, or 'sales_quota', etc.

    class Meta:
        verbose_name = "CRM User"
        verbose_name_plural = "CRM Users"

    def __str__(self):
        return self.get_full_name() or self.username

# --- Base CRM Objects ---

class Account(TenantModel):
    INDUSTRY_CHOICES = [
        ('tech', 'Technology'),
        ('finance', 'Finance'),
        ('healthcare', 'Healthcare'),
        ('manufacturing', 'Manufacturing'),
        ('retail', 'Retail'),
        ('other', 'Other'),
    ]
    TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('prospect', 'Prospect'),
        ('partner', 'Partner'),
        ('reseller', 'Reseller'),
    ]

    name = models.CharField(max_length=100, unique=True)
    website = models.URLField(blank=True, null=True)
    phone = models.CharField(max_length=100, blank=True)
    industry = models.CharField(max_length=100, choices=INDUSTRY_CHOICES, blank=True)
    account_type = models.CharField(max_length=100, choices=TYPE_CHOICES, blank=True)
    description = models.TextField(blank=True)
    annual_revenue = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    employees = models.IntegerField(blank=True, null=True)
    address_street = models.CharField(max_length=200, blank=True)
    address_city = models.CharField(max_length=100, blank=True)
    address_state = models.CharField(max_length=100, blank=True)
    address_zipcode = models.CharField(max_length=100, blank=True)
    address_country = models.CharField(max_length=100, blank=True)

    # Salesforce-like audit fields
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_accounts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_accounts')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_accounts')

    class Meta:
        verbose_name = "Account (Company)"
        verbose_name_plural = "Accounts (Companies)"

    def __str__(self):
        return self.name

class Contact(TenantModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True, unique=True) # Unique if strict
    phone = models.CharField(max_length=100, blank=True)
    mobile = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='contacts') # Contact can belong to an Account
    
    # Salesforce-like audit fields
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_contacts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_contacts')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_contacts')

    class Meta:
        verbose_name = "Contact (Person)"
        verbose_name_plural = "Contacts (People)"
        # unique_together = ('first_name', 'last_name', 'account') # Prevent duplicate contacts for same account

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

#### 2. `sales/models.py` - Leads & Opportunities

class Lead(TenantModel):
    LEAD_STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('unqualified', 'Unqualified'),
        ('converted', 'Converted'), # Convert to Account/Contact/Opportunity
    ]
    LEAD_SOURCE_CHOICES = [
        ('web', 'Web Form'),
        ('referral', 'Referral'),
        ('partner', 'Partner'),
        ('purchased', 'Purchased List'),
        ('event', 'Event'),
        ('other', 'Other'),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=50, choices=LEAD_STATUS_CHOICES, default='new')
    source = models.CharField(max_length=50, choices=LEAD_SOURCE_CHOICES, blank=True)
    description = models.TextField(blank=True)
    
    # Salesforce-like audit fields
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_leads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_leads')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_leads')

    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.company})"

class Opportunity(WorkflowCompatibleModel):
    SALES_STAGE_CHOICES = [
        ('qualification', 'Qualification'),
        ('needs_analysis', 'Needs Analysis'),
        ('value_proposition', 'Value Proposition'),
        ('id_decision_makers', 'Identify Decision Makers'),
        ('perception_analysis', 'Perception Analysis'),
        ('proposal_price', 'Proposal/Price Quote'),
        ('negotiation_review', 'Negotiation/Review'),
        ('closed_won', 'Closed Won'),
        ('closed_lost', 'Closed Lost'),
    ]
    PROBABILITY_CHOICES = [
        (0, '0%'), (10, '10%'), (20, '20%'), (30, '30%'), (40, '40%'),
        (50, '50%'), (60, '60%'), (70, '70%'), (80, '80%'), (90, '90%'), (100, '100%')
    ]

    name = models.CharField(max_length=255)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='opportunities') # Link to an Account
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='opportunities') # Link to a key Contact
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    close_date = models.DateField()
    stage = models.CharField(max_length=100, choices=SALES_STAGE_CHOICES, default='qualification')
    probability = models.IntegerField(choices=PROBABILITY_CHOICES, default=10) # Reflects sales stage
    description = models.TextField(blank=True)
    
    # Salesforce-like audit fields
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_opportunities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_opportunities_vCRM')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_opportunities_vCRM')

    pending_stage = models.CharField(max_length=50, choices=SALES_STAGE_CHOICES, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old_instance = self.__class__.objects.get(pk=self.pk)
                # If stage is being changed and it's not the same as old, 
                # we technically want to intercept this.
                if old_instance.stage != self.stage:
                    # In a formal system, we'd prevent this direct save 
                    # and set pending_stage instead.
                    # For this implementation, we log the intent.
                    logger.info(f"Opportunity {self.name} stage change: {old_instance.stage} -> {self.stage}")
            except Exception:
                pass
        super().save(*args, **kwargs)

    def finalize_workflow(self, actor):
        """
        Logic to execute when a stage transition workflow is approved.
        The 'actor' is the person who approved the final step.
        """
        if self.pending_stage:
            logger.info(f"Updating Opportunity {self.name} from {self.stage} to {self.pending_stage} (Approved by {actor})")
            self.stage = self.pending_stage
            self.pending_stage = None
            self.save()
        else:
            logger.warning(f"Finalize workflow called for {self.name} but no pending_stage found.")

    def trigger_stage_transition(self, new_stage, user):
        """
        Method to initiate a formal stage change request.
        """
        self.pending_stage = new_stage
        self.save()
        
        # Trigger the workflow engine
        # In this project, that means creating a WorkflowInstance
        # and finding the appropriate Workflow definition.
        # This is a placeholder for the actual service call:
        # WorkflowService().initiate_workflow(self, user)
        logger.info(f"Workflow initiated for {self.name} transition to {new_stage} by {user}")
        return True

    class Meta:
        verbose_name = "Opportunity (Sales Deal)"
        verbose_name_plural = "Opportunities (Sales Deals)"

    def __str__(self):
        return str(self.name)
#### 3. `crm_core/models.py` (Continued) - Activities

# ✅ Valid Nigerian phone prefixes (4-digit only)
VALID_PREFIXES = {
    '0809', '0817', '0818', '0909', '0908',  # 9mobile
    '0701', '0708', '0802', '0808', '0812', '0901', '0902', '0904', '0907', '0912', '0911',  # Airtel
    '0705', '0805', '0807', '0811', '0815', '0905', '0915',  # Glo
    '0804',  # Mtel
    '0703', '0706', '0803', '0806', '0810', '0813', '0814', '0816', '0903', '0906', '0913', '0916', '0704', '0707'  # MTN
}

# 📞 Validator for Nigerian phone prefixes
def validate_nigerian_prefix(value):
    if not value.isdigit():
        raise ValidationError("Phone number must contain only digits.")
    if len(value) != 11:
        raise ValidationError("Phone number must be exactly 11 digits.")
    if value[:4] not in VALID_PREFIXES:
        raise ValidationError(f"Phone number must start with a valid Nigerian prefix. Got '{value[:4]}'.")


# 🔢 Validator for 10-digit account number
def validate_account_number(value):
    if not value.isdigit():
        raise ValidationError("Account number must contain only digits.")
    if len(value) != 10:
        raise ValidationError("Account number must be exactly 10 digits.")


class Customer(TenantModel):
    customer_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True, validators=[validate_nigerian_prefix])
    account_number = models.CharField(max_length=20, unique=True, validators=[validate_account_number])

    gender = models.CharField(max_length=10, choices=[("male", "Male"), ("female", "Female")])
    # city_of_residence = models.CharField(max_length=100)
    town_of_residence = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True,related_name='customer_town')
    # state_of_residence = models.CharField(max_length=100)
    
    nationality = models.CharField(max_length=50, default="Nigeria")
    occupation = models.CharField(max_length=100)
    date_of_birth = models.DateField()

    branch = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name='customer_branch')  # Customer's registered branch

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.account_number}"

    def clean(self):
        """Custom validation for phone numbers and account numbers."""
        if not self.phone_number.startswith("0") or self.phone_number[1] not in "6789":
            raise ValueError("Phone number must start with '0' and second digit must be between 6 and 9.")
        if len(self.account_number) != 10 or not self.account_number.isdigit():
            raise ValueError("Account number must be exactly 10 digits.")

class Transaction(TenantModel):
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

    transaction_id = models.CharField(max_length=100, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=100, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    transaction_channel = models.CharField(max_length=100, choices=TRANSACTION_CHANNELS)
    timestamp = models.DateTimeField(auto_now_add=False)
    def __str__(self):
        return f"{self.transaction_type} via {self.transaction_channel} - {self.amount}"


class LoanReport(TenantModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    loan_account_number = models.CharField(max_length=20, unique=True)
    amount_collected = models.DecimalField(max_digits=12, decimal_places=2)
    date_loan_booked = models.DateField()
    last_repayment_date = models.DateField(null=True, blank=True)
    loan_balance = models.DecimalField(max_digits=12, decimal_places=2)

    branch_booked = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)  # Branch where loan was processed

    def __str__(self):
        return f"Loan {self.loan_account_number} - Balance: {self.loan_balance}"

 
class BranchPerformance(TenantModel):
    branch = models.ForeignKey(Location, on_delete=models.CASCADE)
    total_customers = models.PositiveIntegerField()
    total_transactions = models.PositiveIntegerField()
    revenue_generated = models.DecimalField(max_digits=12, decimal_places=2)
    report_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.branch.name} - {self.report_date}"                    
    



class Prompt(TenantModel):
    name = models.CharField(max_length=100, default="standard")
    is_hum_agent_allow_prompt = models.TextField(blank=True, null=True)
    no_hum_agent_allow_prompt = models.TextField(blank=True, null=True)
    summary_prompt = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LLM(TenantModel):
    
    name = models.CharField(max_length=100, null=False) # Ollama, Gemini
    model = models.CharField(max_length=100, null=False)
    # key = Column(String(255), nullable=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

class Tenant_AI(TenantModel):

    prompt_template = models.ForeignKey(Prompt, on_delete=models.SET_NULL, null=True, blank=True)
    
    tenant_website = models.CharField(max_length=255, null=True, blank=True)
    tenant_knowledge_base = models.CharField(max_length=255, null=True, blank=True)
    tenant_text = models.TextField(null=True, blank=True)
    tenant_document = models.TextField(null=True, blank=True)
    
    is_hum_agent_allow = models.BooleanField(default=True)
    conf_level = models.IntegerField(default=40)
    sentiment_threshold = models.FloatField(default=0.0)
    ticket_type = models.JSONField(default=list)
    message_tone = models.CharField(max_length=20, default='Professional')
    
    chatbot_greeting = models.TextField(default="How can I assist you today?")
    agent_node_prompt = models.TextField(default="...", null=True, blank=True)
    final_answer_prompt = models.TextField(null=True, blank=True)
    summary_prompt = models.TextField(null=True, blank=True)
    prompt_type = models.CharField(max_length=50, default="standard")
    db_uri = models.CharField(max_length=512, null=True, blank=True)


class Conversation(TenantModel):

    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    started_at = models.DateTimeField(default=datetime.utcnow)
    updated_at = models.DateTimeField(auto_now=True)
    summary = models.TextField(null=True)
    employee_id = models.CharField(max_length=255, null=True)
    message_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return f"Conversation {self.id} (Session: {self.session_id})"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    text = models.TextField()
    is_user = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)

    class Meta:
        ordering = ['timestamp']
    def __str__(self):
        return f"{'User' if self.is_user else 'Bot'}: {self.text[:50]}..."