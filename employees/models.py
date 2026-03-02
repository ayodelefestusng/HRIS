from ast import Add
import logging
import os
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField

from org.models import Department, Grade, TenantModel, Unit, tenant_directory_path
from .utils import validate_nigerian_phone

logger = logging.getLogger(__name__)
User = get_user_model()


class Gender(models.TextChoices):
    MALE = "M", "Male"
    FEMALE = "F", "Female"
    OTHER = "O", "Other"


class EmploymentStatus(models.TextChoices):
    FULL_TIME = "FT", "Full-Time"
    PART_TIME = "PT", "Part-Time"
    CONTRACTOR = "CO", "Contractor"
    INTERN = "IN", "Intern"


class WorkStatus(models.TextChoices):
    ACTIVE = "A", "Active"
    ON_LEAVE = "L", "On Leave"
    RESIGNED = "R", "Resigned"
    TERMINATED = "T", "Terminated"
    RETIRED = "RE", "Retired"
    DISMISSED = "D", "Dismissed"
    PROBATION = "P", "Probation"
    SUSPENDED = "S", "Suspended"


class Employee(TenantModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employee",
        help_text="Links to the Django user account for login.",
    )
    application = models.ForeignKey(
        "ats.Application",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="application",
        help_text="Link to the application record.",
    )

    employee_id = models.CharField(max_length=20, unique=True, db_index=True)
    employee_email = models.EmailField( unique=True, default=None, help_text="Official employee email")
    line_manager = models.ForeignKey("self", null=True,blank=True,on_delete=models.SET_NULL,related_name="downline",)

    grade = models.ForeignKey("org.Grade", on_delete=models.RESTRICT, related_name="employees")
    grade_base_pay = models.ForeignKey(Grade, on_delete=models.RESTRICT, related_name="grade_pay")
    above_grade_base_pay = models.PositiveIntegerField(default=0,validators=[MinValueValidator(0)],help_text="Additional allowance or bonus",)
    base_pay = models.PositiveIntegerField(default=0,editable=False,help_text="Auto-calculated: grade_base_pay + extra_base_pay",)
    
    above_grade_base_leave = models.PositiveIntegerField(default=0,validators=[MinValueValidator(0)],help_text="Additional allowance or bonus",)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices)

    photo = models.ImageField(
        upload_to="employee_photos/", null=True, blank=True
    )  # NEW

    personal_email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(
        max_length=11,
        validators=[validate_nigerian_phone],
        null=True,
        help_text="11 digits and  a valid phone number format",
    )

    nationality = models.CharField(max_length=100, blank=True, null=True)
    mother_maiden_name = models.CharField(max_length=100, blank=True, null=True)

    address = models.TextField(max_length=255, blank=True, null=True)
    house_number = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    passport_number = models.CharField(
        max_length=20, blank=True, null=True, unique=True
    )
    national_id_number = models.CharField(max_length=20, unique=True)  # REQUIRED now
    driver_license_number = models.CharField(
        max_length=20, blank=True, null=True, unique=True
    )

    bank_name = models.CharField(max_length=100, blank=True, null=True)  # NEW
    account_number = models.CharField(
        max_length=30, blank=True, null=True, unique=True
    )  # NEW

    next_of_kin = models.CharField(max_length=100, blank=True, null=True)
    next_of_kin_phone_number = models.CharField(
        max_length=11,
        validators=[validate_nigerian_phone],
        null=True,
        blank=True,  # Added blank=True
        help_text="11 digits...",
    )
    next_of_kin_email = models.EmailField(blank=True, null=True)

    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone_number = models.CharField(
        max_length=11,
        validators=[validate_nigerian_phone],
        null=True,
        blank=True,  # Added blank=True
        help_text="11 digits...",
    )
    employment_status = models.CharField(
        max_length=2,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.FULL_TIME,
    )

    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    work_status = models.CharField(
        max_length=2,
        choices=WorkStatus.choices,
        default=WorkStatus.ACTIVE,
    )
    
    # Advanced Workflow Fields
    away = models.BooleanField(
        default=False, 
        help_text="True if employee is suspended, on leave, or inactive."
    )
    relief_person = models.ForeignKey(
        "self", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="relief_for",
        help_text="Employee who acts as relief during leave."
    )
    deputy_person = models.ForeignKey(
        "self", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="deputy_for",
        help_text="Deputy head for automatic delegation."
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Employee Record"
        verbose_name_plural = "Employee Records"
        indexes = [
            models.Index(fields=["first_name", "last_name", "tenant"]),
            models.Index(fields=["employee_email", "tenant"]),
        ]

    def clean(self):
        super().clean()
        if self.date_of_birth:
            today = date.today()
            age = (
                today.year
                - self.date_of_birth.year
                - (
                    (today.month, today.day)
                    < (self.date_of_birth.month, self.date_of_birth.day)
                )
            )

            # General rule: must be at least 18 years old unless intern
            if self.employment_status != EmploymentStatus.INTERN and age < 18:
                raise ValidationError(
                    {"date_of_birth": "Employee must be at least 18 years old."}
                )

            # Special rule: interns must be 10 years old or younger
            if self.employment_status == EmploymentStatus.INTERN and age < 10:
                raise ValidationError(
                    {"date_of_birth": "Interns must be 10 years old or older."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        
        # 1. Automated 'away' triggers
        # If dismissed, suspended, or on leave, set away=True
        if self.work_status in [WorkStatus.DISMISSED, WorkStatus.SUSPENDED, WorkStatus.ON_LEAVE]:
            self.away = True
        
        # 2. Base Pay Calculation
        grade_amount = self.grade_base_pay.basic_salary if self.grade_base_pay else 0
        self.base_pay = grade_amount + (self.above_grade_base_pay or 0)

        return super().save(*args, **kwargs)

    @property
    def full_name(self):
        """Return the employee's full name as 'First Last'."""
        return f"{self.first_name} {self.last_name}"

    @property
    def annaul_leave_entitment(self):
        """Return the employee's full name as 'First Last'."""
        return self.grade.annual_leave_days + self.above_grade_base_leave
    @property
    def primary_department(self):
        # Use related_name="roles" from JobRole
        role = self.roles.first()  # not .all()
        return role.org_unit.name if role and role.org_unit else "No Dept"

    @property
    def primary_job_title(self):
        role = self.roles.first()  # consistent with related_name
        return role.job_title.name if role else "No Title"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.primary_department})"


STATUS_CHOICES =[
    ("pending", "Pending"), 
    ("rejected_for_amendment", "Rejected for Amendment"), 
    ("approved", "Approved"), 
    ("rejected", "Rejected")]

class ProfileUpdateRequest(TenantModel):
    """
    Existing model expanded to hold skill updates and 
    PII changes for HR approval.
    """
    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE)
    
    # Existing fields
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    next_of_kin = models.CharField(max_length=255, blank=True, null=True)
    next_of_kin_phone = models.CharField(max_length=20, blank=True, null=True)
    reason = models.TextField(help_text="Why are you requesting this change?")
    
    # Staging for Skills (JSON for flexibility)
    # Format: {"skill_id": level, ...}
    proposed_data = models.JSONField(default=dict, blank=True)
    approval_status = models.CharField(
        max_length=50, 
        choices=STATUS_CHOICES,
        default='pending'
    ) 
    
    
    created_at = models.DateTimeField(auto_now_add=True)
    def apply_workflow_changes(self, actor=None):
        """Logic specific to Profile Updates"""
        emp = self.employee
        
        # 1. Update direct PII fields from the request object
        if self.phone_number:
            emp.phone_number = self.phone_number
        if self.address:
            emp.address = self.address
        if self.next_of_kin:
            emp.next_of_kin = self.next_of_kin
        if self.next_of_kin_phone:
            # Map next_of_kin_phone to next_of_kin_phone_number on Employee
            emp.next_of_kin_phone_number = self.next_of_kin_phone
            
        # 2. Process Skills and other data in proposed_data
        from development.models import EmployeeSkillProfile
        for field, value in self.proposed_data.items():
            # Check if 'field' is a numeric skill ID
            try:
                skill_id = int(field)
                profile, created = EmployeeSkillProfile.objects.update_or_create(
                    employee=emp,
                    skill_id=skill_id,
                    defaults={'level': value, 'tenant': self.tenant, 'source': 'system'}
                )
                logger.info(f"Updated skill {skill_id} to level {value} for {emp.full_name}")
                continue # Successfully handled as a skill
            except (ValueError, TypeError):
                # If field is not an integer, try setting it as an attribute
                if hasattr(emp, field):
                    setattr(emp, field, value)
                else:
                    logger.warning(f"Employee model has no field {field}")
                    
        emp.save()
        
        self.approval_status = "approved"
        self.save()

    def finalize_workflow(self, actor):
        # Move staging data to Employee model
        emp = self.employee
        emp.phone_number = self.phone_number
        # ... update other fields ...
        emp.save()
        self.approval_status = "approved" # Using your preferred state
        self.save()
    def __str__(self):
        return f"Update Request: {self.employee.full_name} ({self.created_at.date()})"


class ProfileUpdateRequestv1(TenantModel):
    """
    Stores proposed changes to an employee's profile.
    These changes are only applied when the associated workflow is approved.
    """

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="profile_updates"
    )

    # Staging fields
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    next_of_kin = models.CharField(max_length=100, blank=True, null=True)
    next_of_kin_phone = models.CharField(max_length=15, blank=True, null=True)

    # Link to the workflow
    workflow_instance = models.OneToOneField(
        "workflow.WorkflowInstance",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile_update_request",
    )

    reason = models.TextField(blank=True, help_text="Reason for update")
    created_at = models.DateTimeField(auto_now_add=True)
    is_applied = models.BooleanField(default=False)
    proposed_data = models.JSONField(default=dict, blank=True)
    from django.core.exceptions import ValidationError

    def clean(self):
        super().clean()
        employee = self.employee
        
        if not isinstance(self.proposed_data, dict):
            raise ValidationError("proposed_data must be a dictionary.")

        for field, value in self.proposed_data.items():
            try:
                # Check if it's a skill ID
                int(field)
            except (ValueError, TypeError):
                # If not a skill, it MUST be a valid field on the Employee model
                if not hasattr(employee, field):
                    raise ValidationError(
                        f"Invalid update: '{field}' is neither a valid Skill ID nor an Employee field."
                    )
    def __str__(self):
        return f"Update Request for {self.employee} ({self.created_at.date()})"
    def apply_workflow_changes(self, actor=None):
        """Logic specific to Profile Updates"""
        employee = self.employee
        
        # 1. Update direct PII fields from the request object
        if self.phone_number:
            employee.phone_number = self.phone_number
        if self.address:
            employee.address = self.address
        if self.next_of_kin:
            employee.next_of_kin = self.next_of_kin
        if self.next_of_kin_phone:
            # Map next_of_kin_phone to next_of_kin_phone_number on Employee
            employee.next_of_kin_phone_number = self.next_of_kin_phone
            
        # 2. Process Skills and other data in proposed_data
        from development.models import EmployeeSkillProfile, Skill
        for field, value in self.proposed_data.items():
            # Check if 'field' is a numeric skill ID
            try:
                skill_id = int(field)

                # Optional: Check if the Skill ID actually exists to avoid IntegrityErrors
                if Skill.objects.filter(id=skill_id).exists():
                    profile, created = EmployeeSkillProfile.objects.update_or_create(
                        employee=employee,
                        skill_id=skill_id,
                        defaults={'level': value, 'tenant': self.tenant, 'source': 'system'}
                    )

            except (ValueError, TypeError):
            # Handle Attribute Updates (String Keys)
                if hasattr(employee, field):
                    setattr(employee, field, value)
                else:
                    logger.warning(f"Skipping update: Field {field} not found on Employee.")    



                    
        employee.save()
        # 3. Finalize Status
        self.status = "approved"
        self.save()


    def apply_changes(self):
        """
        Called when the workflow is Approved.
        Copies staging values to the actual Employee record.
        """
        if self.is_applied:
            return

        emp = self.employee
        if self.phone_number:
            emp.phone_number = self.phone_number
        if self.address:
            emp.address = self.address
        if self.next_of_kin:
            emp.next_of_kin = self.next_of_kin
        if self.next_of_kin_phone:
            emp.next_of_kin_phone_number = self.next_of_kin_phone

        emp.save()
        self.is_applied = True
        self.save()


from org.models import TenantModel
from org.models import tenant_directory_path
class CompanyPolicy(TenantModel):
    """
    World-class: Versioning for policies. When a handbook is updated,
    we need to know who signed the NEW version.
    """

    title = models.CharField(max_length=255)
    version = models.CharField(max_length=10, default="1.0")
    file = models.FileField(upload_to=tenant_directory_path)
    is_active = models.BooleanField(default=True)
    requires_signature = models.BooleanField(default=True)
    effective_date = models.DateField(default=timezone.now)

    class Meta:
        unique_together = ("tenant", "title", "version")


class PolicyAcknowledgement(TenantModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    policy = models.ForeignKey(CompanyPolicy, on_delete=models.CASCADE)
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    digital_signature = models.CharField(
        max_length=100, blank=True, help_text="Hash or IP of the user"
    )
    comments = models.TextField(blank=True, help_text="Optional notes or feedback")

    class Meta:
        unique_together = ("employee", "policy", "tenant")

    def __str__(self):
        return f"{self.employee} acknowledged {self.policy.title} on {self.acknowledged_at.date()}"


class EmployeeDocument(TenantModel):
    DOCUMENT_TYPE_CHOICES = (
        ("CNTR", "Contract"),
        ("NDA", "NDA"),
        ("ID", "Identity Document"),
        ("CERT", "Certification"),
        ("OTR", "Other"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(
        max_length=4, choices=DOCUMENT_TYPE_CHOICES, default="OTR"
    )
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=tenant_directory_path)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee} - {self.name}"


class JobAssignment(TenantModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="job_history"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="job_assignments"
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="job_assignments",
        null=True,
        blank=True,
        help_text="Optional: tie assignment to a specific unit under the department.",
    )
    job_title = models.ForeignKey("org.JobRole", on_delete=models.PROTECT)

    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="team_leads",
        help_text="Manager can be another JobAssignment.",
    )

    employment_status = models.CharField(
        max_length=2,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.FULL_TIME,
    )
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(
        default=True,
        help_text="Only one assignment should be active at any given time.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        unique_together = ("employee", "start_date")

    def __str__(self):
        unit_display = f" / {self.unit.name}" if self.unit else ""
        return f"{self.employee.last_name} - {self.job_title.name} ({self.department.name}{unit_display})"


class CompensationRecord(TenantModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="comp_history"
    )
    salary_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    effective_date = models.DateField(default=timezone.now)
    reason = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_date"]
        unique_together = ("employee", "effective_date")

    def __str__(self):
        return f"{self.employee.last_name} - {self.salary_amount} {self.currency} from {self.effective_date}"


class Admin_Asset(TenantModel):
    ASSET_STATUS = (
        ("AV", "Available"),
        ("AS", "Assigned"),
        ("RS", "Reserved"),
        ("RE", "Retired"),
    )
    name = models.CharField(max_length=255,)
    asset_tag = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=2, choices=ASSET_STATUS, default="AV")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.asset_tag})"


class AssetAssignment(TenantModel):
    asset = models.ForeignKey(
        Admin_Asset, on_delete=models.PROTECT, related_name="assignments"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="admin_assets"
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    returned_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.asset} -> {self.employee}"


class DisciplinaryAction(TenantModel):
    ACTION_TYPES = (
        ("WR", "Written Warning"),
        ("VR", "Verbal Warning"),
        ("SP", "Suspension"),
        ("TR", "Termination"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="disciplinary_actions"
    )
    action_type = models.CharField(max_length=2, choices=ACTION_TYPES)
    description = models.TextField()
    issued_by = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issued_disciplinary_actions",
    )
    date_issued = models.DateField(default=timezone.now)
    follow_up_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.employee} - {self.get_action_type_display()} on {self.date_issued}"
        )


class Benefit(TenantModel):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    provider = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.name


class EmployeeBenefit(TenantModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="benefits"
    )
    benefit = models.ForeignKey(
        Benefit, on_delete=models.CASCADE, related_name="enrollments"
    )
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("employee", "benefit", "start_date")

    def __str__(self):
        return f"{self.employee} → {self.benefit}"


class ExitProcess(TenantModel):
    EXIT_TYPES = [
        ("RESIGNATION", "Resignation"),
        ("TERMINATION", "Termination"),
        ("RETIREMENT", "Retirement"),
    ]
    STATUS_CHOICES = [
        ("INITIATED", "Initiated"),
        ("CLEARANCE", "Clearance Phase"),
        (
            "leave_application",
            "Final Interview",
        ),  # Using your custom state for the meeting phase
        ("EXITED", "Exit Completed"),
    ]

    employee = models.OneToOneField(
        Employee, on_delete=models.CASCADE, related_name="exit_process"
    )
    exit_type = models.CharField(max_length=20, choices=EXIT_TYPES)
    notice_date = models.DateField(auto_now_add=True)
    last_working_day = models.DateField()
    reason_for_leaving = models.TextField(blank=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="INITIATED"
    )
    is_eligible_for_rehire = models.BooleanField(default=True)

    # Clearance Progress
    it_cleared = models.BooleanField(default=False)
    finance_cleared = models.BooleanField(default=False)
    hr_cleared = models.BooleanField(default=False)

    def __str__(self):
        return f"Exit: {self.employee.last_name} ({self.last_working_day})"


# @receiver(post_delete, sender=EmployeeDocument)
# def auto_delete_employee_document_file(sender, instance, **kwargs):
#     """Deletes file from filesystem when an EmployeeDocument is deleted."""
#     if instance.file and os.path.isfile(instance.file.path):
#         os.remove(instance.file.path)

# @receiver(post_delete, sender=CompanyPolicy)
# def auto_delete_company_policy_file(sender, instance, **kwargs):
#     """Deletes file from filesystem when a CompanyPolicy is deleted."""
#     if instance.file and os.path.isfile(instance.file.path):
#         os.remove(instance.file.path)


class Survey(TenantModel):
    """
    Represents an employee engagement survey with multiple questions.
    Example: Annual Engagement Survey.
    """

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    is_anonymous = models.BooleanField(default=True)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title


class SurveyQuestion(TenantModel):
    """
    Individual question in a survey.
    """

    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="questions"
    )
    text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=[
            ("TEXT", "Text"),
            ("SCALE", "Scale (1-5)"),
            ("CHOICE", "Multiple Choice"),
        ],
        default="TEXT",
    )

    def __str__(self):
        return f"{self.survey.title} - {self.text}"


class SurveyResponse(TenantModel):
    """
    Stores an employee's response to a survey question.
    """

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="survey_responses"
    )
    question = models.ForeignKey(
        SurveyQuestion, on_delete=models.CASCADE, related_name="responses"
    )
    answer_text = models.TextField(blank=True)
    answer_scale = models.IntegerField(null=True, blank=True)
    answer_choice = models.CharField(max_length=200, blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.employee} - {self.question.text}"


class Poll(TenantModel):
    """
    Quick poll for employees to vote on a single question.
    Example: 'Preferred team outing activity'.
    """

    question = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.question


class PollOption(TenantModel):
    """
    Options for a poll question.
    """

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.poll.question} - {self.text}"


class PollVote(TenantModel):
    """
    Employee vote in a poll.
    """

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="poll_votes"
    )
    option = models.ForeignKey(
        PollOption, on_delete=models.CASCADE, related_name="votes"
    )
    voted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.employee} voted {self.option.text}"


class PulseCheck(TenantModel):
    """
    Short, frequent engagement check (e.g., weekly mood check).
    """

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="pulse_checks"
    )
    score = models.IntegerField(help_text="Scale 1-10 for mood/engagement")
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.employee} - {self.score}"


# class Survey(TenantModel):
#     title = models.CharField(max_length=255)
#     description = models.TextField(blank=True)
#     is_anonymous = models.BooleanField(default=True)
#     start_date = models.DateField(default=timezone.now)
#     end_date = models.DateField(null=True, blank=True)

#     def __str__(self):
#         return self.title


# class SurveyQuestion(TenantModel):
#     QUESTION_TYPES = (
#         ("TXT", "Text"),
#         ("SCL", "Scale"),
#         ("MCQ", "Multiple Choice"),
#     )
#     survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="questions")
#     text = models.CharField(max_length=500)
#     question_type = models.CharField(max_length=3, choices=QUESTION_TYPES, default="TXT")

#     def __str__(self):
#         return self.text


# class SurveyResponse(TenantModel):
#     survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="responses")
#     employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL)
#     submitted_at = models.DateTimeField(auto_now_add=True)
#     is_anonymous = models.BooleanField(default=True)
#     def __str__(self):
#         return f"Response to {self.survey} by {self.employee if self.employee else 'Anonymous'}"


# class SurveyAnswer(TenantModel):
#     response = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE, related_name="answers")
#     question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE)
#     answer_text = models.TextField()
#     answer_scale = models.PositiveSmallIntegerField(null=True, blank=True)
#     answer_choice = models.CharField(max_length=255, blank=True)
#     def __str__(self):
#         return f"Answer to {self.question} in {self.response}"


# class JobTitle(TenantModel):
#     name = models.CharField(max_length=100, unique=True)
#     description = models.TextField(blank=True)

# ... existing code ...





class EmployeeChangeRequest(TenantModel):
    """
    Acts as a staging area for Employee updates. Data is only 
    merged into the main Employee model upon final approval.
    """
    STATUS_CHOICES =[
    ("pending", "Pending"), 
    ("rejected_for_amendment", "Rejected for Amendment"), 
    ("approved", "Approved"), 
    ("rejected", "Rejected")]

    employee = models.ForeignKey(
        "employees.Employee", 
        on_delete=models.CASCADE,
        related_name="change_requests",
        help_text="The employee whose details are being updated.")
    proposed_data = models.JSONField(
        default=dict,
        help_text="A dictionary of fields to update (e.g., {'base_pay': 5000, 'skills': {1: 5}}).")
    justification = models.TextField(
        blank=True, 
        help_text="Reason for the change request.")
    approval_status = models.CharField(
        max_length=50, 
        choices=STATUS_CHOICES, 
        default='pending',
        help_text="Current state of the change request.")
    approval_date = models.DateField(
        null=True, 
        blank=True,
        help_text="When these changes should technically take effect.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    

    def __str__(self):
        return f"CR-{self.id} for {self.employee.full_name}"

    class Meta:
        verbose_name = "Employee Change Request"
        ordering = ['-created_at']
