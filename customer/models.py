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
import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import RegexValidator
from decimal import Decimal
import random
import uuid
from datetime import timedelta

logger = logging.getLogger(__name__)
# Extending Django's User model for CRM-specific fields
class CRMUser(TenantModel):
    """
    Represents an internal CRM user with specific roles and permissions.
    Extends TenantModel to support multi-tenancy.
    """
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
    """
    Represents a company or organization that is a business entity in the CRM.
    Stores contact information, industry details, and audit fields.
    """
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
    """
    Represents an individual person associated with an Account.
    Used for tracking personal interaction details like email, phone, and title.
    """
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
    """
    Represents a potential customer or sales prospect before they are qualified.
    Contains basic contact info and source tracking.
    """
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
    """
    Represents a qualified sales deal or potential revenue-generating event.
    Tracked through various stages of the sales pipeline via workflow.
    """
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
    """
    Validates that the provided phone number starts with a valid Nigerian mobile prefix.
    """
    if not value.isdigit():
        raise ValidationError("Phone number must contain only digits.")
    if len(value) != 11:
        raise ValidationError("Phone number must be exactly 11 digits.")
    if value[:4] not in VALID_PREFIXES:
        raise ValidationError(f"Phone number must start with a valid Nigerian prefix. Got '{value[:4]}'.")


# 🔢 Validator for 10-digit account number
def validate_account_number(value):
    """
    Validates that the provided bank account number is exactly 10 digits.
    """
    if not value.isdigit():
        raise ValidationError("Account number must contain only digits.")
    if len(value) != 10:
        raise ValidationError("Account number must be exactly 10 digits.")
validate_nin = RegexValidator(
    regex=r'^\d{11}$',
    message="NIN must be exactly 11 digits.",
)

PASSWORD_COMPLEXITY_HELP = (
    "Must be at least 8 characters and contain an uppercase letter, "
    "a lowercase letter, a digit, and a special character (@$!%*?&#)."
)


class Customer(TenantModel):
    """
    Represents an individual retail or commercial banking customer.
    Stores personal identification, contact details, account number, and branch association.
    """
    customer_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True, validators=[validate_nigerian_prefix])
    account_number = models.CharField(max_length=20, unique=True, validators=[validate_account_number])
     # ── NEW FIELDS ────────────────────────────────────────────────────────────
    nin = models.CharField(
        max_length=11,
        # null=True,
        # blank=True, 
        unique=True,
        validators=[validate_nin],
        help_text="11-digit National Identification Number (NIN).",
    )
    password = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="PBKDF2-hashed service password.  Never store plain text.",
    )

    authenticated = models.BooleanField(default=False)
    password_created = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_expiry = models.DateTimeField(null=True, blank=True)
    otp_used = models.BooleanField(default=False)
     # New fields for PIN lockout
    password_attempts = models.IntegerField(default=0)  # count failed attempts
    password_locked = models.BooleanField(default=False)  # lock status
    # ── END NEW FIELDS ────────────────────────────────────────────────────────

    gender = models.CharField(max_length=10, choices=[("male", "Male"), ("female", "Female")])
    # city_of_residence = models.CharField(max_length=100)
    town_of_residence = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True,related_name='customer_town')
    # state_of_residence = models.CharField(max_length=100)
    
    nationality = models.CharField(max_length=50, default="Nigeria")
    occupation = models.CharField(max_length=100)
    date_of_birth = models.DateField()

    branch = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name='customer_branch')  # Customer's registered branch
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def has_password(self) -> bool:
        """True once the customer has completed the password-creation flow."""
        return bool(self.password)

    def set_password(self, raw_password: str) -> None:
        """Hash and store a new password."""
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Verify a plain-text password against the stored hash."""
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.first_name} – {self.account_number}"

    def clean(self):
        """Custom field-level validation (unchanged from original)."""
        if not self.phone_number.startswith("0") or self.phone_number[1] not in "6789":
            raise ValueError(
                "Phone number must start with '0' and second digit must be 6–9."
            )
        if len(self.account_number) != 10 or not self.account_number.isdigit():
            raise ValueError("Account number must be exactly 10 digits.")
        if len(self.nin) != 11 or not self.nin.isdigit():
            raise ValueError("NIN must be exactly 11 digits.")
    # def __str__(self):
    #     return f"{self.first_name} {self.last_name} - {self.account_number}"

    # def clean(self):
    #     """Custom validation for phone numbers and account numbers."""
    #     if not self.phone_number.startswith("0") or self.phone_number[1] not in "6789":
    #         raise ValueError("Phone number must start with '0' and second digit must be between 6 and 9.")
    #     if len(self.account_number) != 10 or not self.account_number.isdigit():
    #         raise ValueError("Account number must be exactly 10 digits.")

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ["created_at","last_name", "first_name"]
        


# ──────────────────────────────────────────────────────────────────────────────
# 2.  PASSWORD SETUP TOKEN  (new)
# ──────────────────────────────────────────────────────────────────────────────

class PasswordSetupToken(TenantModel):
    """
    Single-use, time-limited token that gates the password-creation page.

    Lifecycle
      1. Created  → tool generates link: /banking/set-password/<token>/
      2. Customer opens link → view validates token (unused + not expired)
      3. Customer submits password → token marked used, redirect to success
      4. Any subsequent visit returns 410 Gone
    """
    token       = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer    = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="password_setup_tokens",
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()          # set to created_at + 24 h by the tool
    is_used     = models.BooleanField(default=False)

    # ── Helpers ───────────────────────────────────────────────────────────────
    @property
    def is_valid(self) -> bool:
        """True iff the token has not been used and has not expired."""
        return (not self.is_used) and (timezone.now() < self.expires_at)

    def mark_used(self) -> None:
        self.is_used = True
        self.save(update_fields=["is_used"])

    def __str__(self):
        status = "used" if self.is_used else ("expired" if not self.is_valid else "valid")
        return f"Token({self.token}) → {self.customer.account_number} [{status}]"

    class Meta:
        verbose_name = "Password Setup Token"
        verbose_name_plural = "Password Setup Tokens"
        ordering = ["-created_at"]

"""
otp_model_addition.py
────────────────────────────────────────────────────────────────────────────────
Add to your existing models.py.

New model:  PasswordResetOTP
  – Stores a 6-digit single-use OTP tied to a Customer.
  – Expires in OTP_EXPIRY_SECONDS (10 s) after creation.
  – Once used it cannot be reused.

Migration
  python manage.py makemigrations && python manage.py migrate
"""


# Adjust these imports to match your project layout
# from .models import Customer
# from .base_models import TenantModel

OTP_EXPIRY_SECONDS = 10          # tight window – intentional
OTP_RESET_CHARGE   = 10          # ₦ debited before OTP is sent


class PasswordResetOTP(TenantModel):
    """
    A single-use, 10-second OTP that gates the password-reset flow.

    Lifecycle
      1. Tool creates record → OTP sent to customer via SMS.
      2. Customer replies with OTP in WhatsApp within 10 s.
      3. Tool validates:  not used  AND  timezone.now() < expires_at
      4. On success:      is_used = True, tool emits a PasswordSetupToken link.
      5. Any later attempt returns "OTP expired or already used."
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer    = models.ForeignKey(
        "Customer",                        # string ref avoids circular import
        on_delete=models.CASCADE,
        related_name="password_reset_otps",
    )
    otp_code    = models.CharField(max_length=6)
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()   # created_at + OTP_EXPIRY_SECONDS
    is_used     = models.BooleanField(default=False)
    charge_ref  = models.CharField(
        max_length=100, blank=True, default="",
        help_text="VFD transaction reference for the ₦10 debit.",
    )

    # ── Class helpers ─────────────────────────────────────────────────────────
    @classmethod
    def generate_for(cls, customer, tenant=None) -> "PasswordResetOTP":
        """Create and return a fresh OTP record (does NOT send SMS)."""
        code = f"{random.randint(0, 999999):06d}"   # zero-padded 6-digit
        obj  = cls.objects.create(
            customer   = customer,
            tenant     = tenant or (customer.tenant if hasattr(customer, 'tenant') else None),
            otp_code   = code,
            expires_at = timezone.now() + timedelta(seconds=OTP_EXPIRY_SECONDS),
        )
        return obj

    # ── Instance helpers ──────────────────────────────────────────────────────
    @property
    def is_valid(self) -> bool:
        return (not self.is_used) and (timezone.now() < self.expires_at)

    @property
    def seconds_remaining(self) -> int:
        delta = (self.expires_at - timezone.now()).total_seconds()
        return max(0, int(delta))

    def mark_used(self) -> None:
        self.is_used = True
        self.save(update_fields=["is_used"])

    def __str__(self):
        status = "valid" if self.is_valid else ("used" if self.is_used else "expired")
        return f"OTP({self.otp_code}) → {self.customer.phone_number} [{status}]"

    class Meta:
        verbose_name        = "Password Reset OTP"
        verbose_name_plural = "Password Reset OTPs"
        ordering            = ["-created_at"]
        # Ensure only one active (unused) OTP per customer at a time
        indexes = [
            models.Index(fields=["customer", "is_used", "expires_at"]),
        ]


# ──────────────────────────────────────────────────────────────────────────────
# 3.  LOAN PROFILE  (new)
# ──────────────────────────────────────────────────────────────────────────────
class LoanTier(TenantModel):

    name = models.CharField(max_length=20, choices=[
        ('Bronze', 'Bronze'),
        ('Silver', 'Silver'),
        ('Gold', 'Gold')
    ], default='Bronze')
    
    loan_limit = models.DecimalField(max_digits=12, decimal_places=2)
    monthly_interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Monthly interest rate as a percentage (e.g. 2.5 for 2.5%)"
    )
    process_fee = models.DecimalField(max_digits=12, decimal_places=2)
    late_fee = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(null=True, blank=True)

    
    def __str__(self):
        return f"{self.name} - Limit: ₦{self.loan_limit} @ {self.monthly_interest_rate}%"
    class Meta:
     unique_together = ('tenant', 'name')
    
class LoanProfile(TenantModel):   # swap → TenantModel in your project
    """
    Captures credit-bureau data, social-media metrics, and AI-driven loan
    eligibility for a customer.

    Re-validation rule
      • If `last_evaluated` is None  OR  older than 180 days  → refresh required.
      • The tool checks `needs_revalidation()` before returning cached results.
    """

    customer       = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="loan_profile",
        to_field="account_number",      # link via account number
    )
    account_number = models.CharField(max_length=20, db_index=True)
    loan_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # ── Credit Bureau ─────────────────────────────────────────────────────────
    credit_rating           = models.CharField(max_length=10,  blank=True, default="")
    credit_score            = models.IntegerField(null=True,   blank=True)
    credit_bureau_reference = models.CharField(max_length=100, blank=True, default="")
    credit_bureau_last_checked = models.DateTimeField(null=True, blank=True)

    # ── Social Media URLs ─────────────────────────────────────────────────────
    facebook_url   = models.URLField(blank=True, default="")
    linkedin_url   = models.URLField(blank=True, default="")
    instagram_url  = models.URLField(blank=True, default="")
    twitter_url    = models.URLField(blank=True, default="")
    tiktok_url     = models.URLField(blank=True, default="")

    # ── Social Media Activity Metrics ─────────────────────────────────────────
    facebook_followers     = models.PositiveIntegerField(default=0)
    facebook_posts_30d     = models.PositiveIntegerField(default=0)
    linkedin_connections   = models.PositiveIntegerField(default=0)
    linkedin_posts_30d     = models.PositiveIntegerField(default=0)
    instagram_followers    = models.PositiveIntegerField(default=0)
    instagram_posts_30d    = models.PositiveIntegerField(default=0)
    twitter_followers      = models.PositiveIntegerField(default=0)
    twitter_tweets_30d     = models.PositiveIntegerField(default=0)
    tiktok_followers       = models.PositiveIntegerField(default=0)
    tiktok_videos_30d      = models.PositiveIntegerField(default=0)
    overall_engagement_score = models.FloatField(null=True, blank=True,
        help_text="Normalised 0–100 composite engagement score derived by AI.")

    # ── AI Eligibility Evaluation ─────────────────────────────────────────────
    loan_eligibility_score  = models.FloatField(
        null=True, blank=True,
        help_text="AI-computed eligibility score 0–100.",
    )
    eligibility_band = models.CharField(
        max_length=20, blank=True, default="",
        choices=[
            ("excellent", "Excellent (80–100)"),
            ("good",      "Good (60–79)"),
            ("fair",      "Fair (40–59)"),
            ("poor",      "Poor (0–39)"),
        ],
        help_text="Derived band based on eligibility score.",
    )
    eligibility_notes  = models.TextField(blank=True, default="")
    raw_ai_response    = models.TextField(blank=True, default="",
        help_text="Full JSON blob returned by the LLM evaluation call.")
    last_evaluated     = models.DateTimeField(null=True, blank=True)

    # ── Helpers ───────────────────────────────────────────────────────────────
    REVALIDATION_DAYS = 180

    def needs_revalidation(self) -> bool:
        """Returns True if data is missing or older than REVALIDATION_DAYS."""
        if not self.last_evaluated:
            return True
        age = (timezone.now() - self.last_evaluated).days
        return age > self.REVALIDATION_DAYS

    def set_eligibility_band(self) -> None:
        """Auto-derive band from score. Call after setting loan_eligibility_score."""
        score = self.loan_eligibility_score or 0
        if score >= 80:
            self.eligibility_band = "excellent"
        elif score >= 60:
            self.eligibility_band = "good"
        elif score >= 40:
            self.eligibility_band = "fair"
        else:
            self.eligibility_band = "poor"

    def __str__(self):
        return (
            f"LoanProfile({self.account_number}) "
            f"score={self.loan_eligibility_score} band={self.eligibility_band}"
        )

    class Meta:
        verbose_name = "Loan Profile"
        verbose_name_plural = "Loan Profiles"

class LoanApplication(TenantModel):
    # 🔹 Core Identity
    loan_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    profile = models.ForeignKey(LoanProfile, on_delete=models.CASCADE, related_name='applications')
    loan_tier = models.ForeignKey(LoanTier, on_delete=models.CASCADE, related_name='loan_tier')
    # status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    # 🔹 Loan Details
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    tenor = models.IntegerField(help_text="Loan duration in months")
    # interest = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    # repayment_start_date = models.DateTimeField(_("Repayment start date"), null=True, blank=True)
    # loan_purpose = models.CharField(max_length=200, null=True, blank=True)
    # collateral = models.CharField("Collateral Offered (if any)", max_length=200, null=True, blank=True)

    # 🔹 Financial Calculations (auto-calculated)
    monthly_repayment = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_loan_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    # 🔹 Banking Info
    bank = models.CharField(max_length=100, null=True, blank=True)
    date_user_accept =  models.DateTimeField(auto_now_add=False)
    # accepted_by_approver = models.BooleanField(default=True)
    disbursed = models.BooleanField(default=True)
    # date_dibursed = models.DateTimeField(_("Date disbursed"), null=True, blank=True)

    current_loan_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # 🔹 Social Media Evaluation
    highest_sentiment_comment = models.TextField(null=True, blank=True)
    highest_sentiment_date = models.DateTimeField(null=True, blank=True)
    highest_sentiment_channel = models.CharField(max_length=50, null=True, blank=True)
    
    lowest_sentiment_comment = models.TextField(null=True, blank=True)
    lowest_sentiment_date = models.DateTimeField(null=True, blank=True)
    lowest_sentiment_channel = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"Loan Application #{self.loan_id} for {self.profile.name}"

    def save(self, *args, **kwargs):
        interest_rate = Decimal(self.loan_tier.monthly_interest_rate) / 100
        principal = self.amount_requested
        monthly_interest = principal * interest_rate
        self.monthly_repayment = principal + monthly_interest
        self.total_loan_due = self.monthly_repayment * self.tenor


        # self.monthly_repayment = self.amount_requested + (self.amount_requested * interest_rate)
        # self.total_loan_due = self.monthly_repayment * self.tenor
        super().save(*args, **kwargs)




class Transaction(TenantModel):
    """
    Records a financial activity performed by a Customer.
    Tracks amount, type (deposit, transfer, etc.), and the channel used (ATM, Mobile, etc.).
    """
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
    """
    Stores snapshots of customer loan balances and repayment statuses.
    Used for tracking portfolio health and individual loan performance.
    """
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
    """
    Aggregates performance metrics for a specific bank branch.
    Tracks total customers, transaction counts, and revenue generated over time.
    """
    branch = models.ForeignKey(Location, on_delete=models.CASCADE)
    total_customers = models.PositiveIntegerField()
    total_transactions = models.PositiveIntegerField()
    revenue_generated = models.DecimalField(max_digits=12, decimal_places=2)
    report_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.branch.name} - {self.report_date}"                    
    



class Prompt(TenantModel):
    """
    Stores system-level prompt templates used by the AI chatbot.
    Allows for dynamic adjustment of bot personality and behavior per tenant.
    """
    name = models.CharField(max_length=100, default="standard")
    is_hum_agent_allow_prompt = models.TextField(blank=True, null=True)
    no_hum_agent_allow_prompt = models.TextField(blank=True, null=True)
    summary_prompt = models.TextField(blank=True, null=True)
    agent_prompt = models.TextField(blank=True, null=True)
    global_answer_prompt = models.TextField(blank=True, null=True)
    tool_intent_map = models.JSONField(blank=True, null=True)
    biller_items = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LLM(TenantModel):
    """
    Configuration for Large Language Model instances (e.g., Gemini, Ollama).
    Maps tenant-specific AI settings to the underlying model provider.
    """
    
    name = models.CharField(max_length=100, null=False) # Ollama, Gemini
    model = models.CharField(max_length=100, null=False)
    # key = Column(String(255), nullable=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
     return f"{self.name} - {self.model}"

    

class Tenant_AI(TenantModel):
    """
    Central configuration model for a tenant's AI chatbot experience.
    Defines thresholds, tones, target channels, and database connection strings.
    """

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
    
    def __str__(self):
        tenant_code = self.tenant.code if self.tenant else "Unknown"
        return f"{tenant_code} - {self.prompt_type}"


class Conversation(TenantModel):
    """
    Represents a single chat session between a user and the AI.
    Used for tracking message history, session duration, and generating summaries.
    """

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
    """
    An individual message within a Conversation.
    Stores the text content, sender (User vs Bot), and any file attachments.
    """
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    text = models.TextField()
    is_user = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to='chat_attachments/', null=True, blank=True)

    class Meta:
        ordering = ['timestamp']
    def __str__(self):
        return f"{'User' if self.is_user else 'Bot'}: {self.text[:50]}..."