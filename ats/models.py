import logging
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from org.models import JobRole, TenantModel, Location
from employees.models import Employee, EmploymentStatus, Unit
from org.models import OrgUnit
from development.models import Skill, Competency
from employees.utils import validate_nigerian_phone
# ats/models.py
import uuid
from django.utils import timezone
from datetime import timedelta


from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone
from employees.models import Employee
from org.models import TenantModel


import logging
from django.db import models
from org.models import TenantModel

# from ats.models import Application
from employees.models import Employee

from django.db import models
from workflow.models import WorkflowDocument, WorkflowStage, WorkflowInstance

logger = logging.getLogger(__name__)
from org.models import (
    tenant_directory_path,
    CompanySize,
    CompanyTier,
    QualificationLevel,
)
import datetime
from django.db import models, transaction
from tinymce.models import HTMLField

class JobPosting(TenantModel):
    STATUS_CHOICES = (("OPEN", "Open"), ("CLOSED", "Closed"), ("DRAFT", "Draft"))

    # title = models.CharField(max_length=200)
    role = models.ForeignKey(
        JobRole, on_delete=models.PROTECT, related_name="job_postings", null=True
    )
    description = models.TextField()
    # description = HTMLField()   # This will use TinyMCE editor
    requirements = models.TextField()
    locations = models.ManyToManyField(Location, related_name="job_postings")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OPEN")
    employment_type = models.CharField(
        max_length=2,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.FULL_TIME,
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_closed  = models.BooleanField(default=False, help_text="The Job status "
    )

    application_url = models.URLField(max_length=500, blank=True, null=True)
    ai_enabled = models.BooleanField(default=False, help_text="Enable AI processing for candidate applications")

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("ats:candidate_apply", kwargs={"job_id": self.pk})
    job_id = models.CharField(max_length=50, editable=False)
    # application_url =models.CharField(max_length=50, editable=False)
    class Meta:
        unique_together = ("tenant", "role","status",)

    def clean(self):
        super().clean()
        
        # Safety Check: Ensure the Role belongs to the same Tenant as the Job
        if self.role and self.tenant:
            if self.role.tenant != self.tenant:
                raise ValidationError(
                    "The selected Job Role must belong to the same tenant."
                )

    def save(self, *args, **kwargs):
        #Auto close
        if self.closing_date and self.closing_date < datetime.date.today():
            self.is_closed = True
        if not self.job_id:
            year = datetime.date.today().year
            # Get prefix from OrgUnit or Role (e.g., 'FIN' from Finance)
            prefix = (
                self.role.org_unit.code.upper() if self.role.org_unit.code else "JOB"
            )

            with transaction.atomic():
                # Count existing jobs for this tenant this year to get the sequence
                last_job = (
                    JobPosting.objects.filter(
                        tenant=self.tenant, job_id__contains=f"-{year}-"
                    )
                    .order_by("-job_id")
                    .first()
                )

                if last_job:
                    # Extract '0001' from 'FIN-2026-0001', increment it
                    last_num = int(last_job.job_id.split("-")[-1])
                    new_num = str(last_num + 1).zfill(4)
                else:
                    new_num = "0001"

                self.job_id = f"{prefix}-{year}-{new_num}"

        # Ensure application_url is set
        if not self.application_url:
            from django.urls import reverse
            # We use a placeholder for domain if not available, but usually this is set in views.
            # However, for consistency, we set the relative path at least.
            path = reverse("ats:candidate_apply", kwargs={"job_id": self.pk if self.pk else 0})
            self.application_url = path

        super().save(*args, **kwargs)

    @property
    def title(self):
        if self.role and self.role.job_title:
            return self.role.job_title.name
        return "Untitled Job"

    def __str__(self):
        return f"{self.role} → {str(self.id)}"


class RecruiterTag(TenantModel):
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#6c757d")  # Hex code

    class Meta:
        unique_together = ("tenant", "name")

    def __str__(self):
        return self.name


class Candidate(TenantModel):
    """Consolidated Applicant/Candidate model for simplicity and speed."""

    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(
        max_length=11,
        validators=[validate_nigerian_phone],
        help_text="11 digits and  a valid phone number format",
    )

    resume = models.FileField(upload_to=tenant_directory_path, null=True, blank=True)
    notes = models.TextField(blank=True)

    preferred_location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_candidates",
        help_text="Candidate's preferred job location",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    tags = models.ManyToManyField(RecruiterTag, blank=True)
    referred_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="candidate_referrals",
    )
    is_anonymized = models.BooleanField(default=False)
    is_anonymized_at = models.DateTimeField(null=True, blank=True)
    data_consent_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "email")

    def __str__(self):
        return self.full_name

    def get_detailed_scorecard(self, job_posting):
        """
        Calculates a detailed score for the candidate based on a specific job posting.
        """
        from org.models import RoleSkillRequirement, RoleCompetencyRequirement
        
        role = job_posting.role
        if not role:
            return {
                'total_score': 0, 'experience_points': 0, 'education_points': 0,
                'skill_score': 0, 'competency_score': 0, 'skills': [], 'competencies': [],
                'skill_match_percent': 0, 'meets_min_exp': False
            }

        # --- 1. Experience & Education ---
        exp_score = sum(exp.calculated_weight for exp in self.experience.all())
        edu_score = sum(edu.weight for edu in self.education.all())

        # --- 2. Skill Alignment ---
        skill_score = 0
        skill_details = []
        role_skills = RoleSkillRequirement.objects.filter(role=role)
        
        for req in role_skills:
            profile = self.skill_profiles.filter(skill=req.skill_name).first()
            candidate_level = profile.level if profile else 0
            
            points = 0
            if candidate_level >= req.required_level:
                # 10 points per skill if level met, +2 bonus for exceeding
                points = 10 + (2 if candidate_level > req.required_level else 0)
            
            skill_score += points
            skill_details.append({
                'name': req.skill_name.name if req.skill_name else "Unknown Skill",
                'required': req.required_level,
                'actual': candidate_level,
                'points': points
            })

        # --- 3. Competency Alignment ---
        comp_score = 0
        comp_details = []
        role_comps = RoleCompetencyRequirement.objects.filter(role=role)
        
        for req in role_comps:
            profile = self.competency_profiles.filter(competency=req.competency).first()
            candidate_level = profile.level if profile else 0
            
            # Scoring: (Level * Weight)
            points = candidate_level * req.weight
            
            comp_score += points
            comp_details.append({
                'name': req.competency.name if req.competency else "Unknown Competency",
                'required': req.required_level,
                'actual': candidate_level,
                'weight': req.weight,
                'points': points
            })

        total_score = exp_score + edu_score + skill_score + comp_score
        
        # Calculate skill match percent
        skill_match_percent = 0
        if role_skills.exists():
            matches = sum(1 for s in skill_details if s['actual'] >= s['required'])
            skill_match_percent = (matches / role_skills.count()) * 100

        return {
            'total_score': total_score,
            'experience_points': exp_score,
            'education_points': edu_score,
            'skill_score': skill_score,
            'competency_score': comp_score,
            'skills': skill_details,
            'competencies': comp_details,
            'skill_match_percent': round(skill_match_percent, 2),
            'meets_min_exp': sum(e.calculate_tenure_years() for e in self.experience.all()) >= (role.min_years_experience or 0)
        }


class CandidateSkillProfile(TenantModel):
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="skill_profiles"
    )
    skill = models.ForeignKey(
        Skill, on_delete=models.CASCADE, related_name="candidate_skill_profiles"
    )
    level = models.PositiveSmallIntegerField(
        default=1, help_text="Inferred or assessed level (1-5)."
    )

    class Meta:
        unique_together = ("candidate", "skill")

    def __str__(self):
        return f"{self.candidate} → {self.skill} (lvl={self.level})"


class CandidateCompetencyProfile(TenantModel):
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name="competency_profiles",
    )
    competency = models.ForeignKey(
        Competency,
        on_delete=models.CASCADE,
        related_name="candidate_competency_profiles",
    )
    level = models.PositiveSmallIntegerField(
        default=1,
        help_text="Competency level (1–5).",
    )

    class Meta:
        unique_together = ("candidate", "competency")

    def __str__(self):
        return f"{self.candidate} → {self.competency} (lvl={self.level})"


class RecruitmentStage(TenantModel):
    """
    Customizable recruitment workflow stages.
    """

    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(
        default=0, help_text="Order in the pipeline (low to high)"
    )
    is_system_stage = models.BooleanField(
        default=False, help_text="Cannot be deleted if True (e.g. Applied, Hired)"
    )

    class Meta:
        ordering = ["order"]
        unique_together = ("tenant", "name")

    def __str__(self):
        return self.name


class Application(TenantModel):
    STAGE_CHOICES = [
        ("APPLIED", "Applied"),
        ("SCREENING", "Screening"),
        ("SCHEDULED FOR INTERVIEW", "Scheduled for Interview"),

        ("INTERVIEWED", "Interviewed"),
        ("OFFER", "Offer"),
        ("HIRED", "Hired"),
        ("REJECTED", "Rejected"),
    ]

    application_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="applications",
    )
    job_posting = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name="applications"
    )
    status = models.CharField(max_length=50, choices=STAGE_CHOICES, default="APPLIED")
    current_stage = models.ForeignKey(
        RecruitmentStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    education_score = models.FloatField(null=True, blank=True)
    experience_score = models.FloatField(null=True, blank=True)
    skill_score = models.FloatField(null=True, blank=True)
    competency_score = models.FloatField(null=True, blank=True)
    evaluation_score = models.FloatField(null=True, blank=True)
    ai_comments = models.TextField(blank=True, null=True, help_text="AI-generated insights and recommendations for this application")

    def __str__(self):
        return f"{self.candidate} -> {self.job_posting.title}-{self.application_id}"

    def save(self, *args, **kwargs):
        from workflow.services.workflow_service import get_detailed_scorecard
        
        is_new = self._state.adding
        
        # Scoring logic (only if already saved or about to be saved)
        if self.candidate and self.job_posting:
            try:
                scorecard = get_detailed_scorecard(self.candidate, self.job_posting)
                self.evaluation_score = scorecard.get("total_score", 0)
                self.education_score = scorecard.get("education_points", 0)
                self.experience_score = scorecard.get("experience_points", 0)
                self.skill_score = scorecard.get("skill_score", 0)
                self.competency_score = scorecard.get("competency_score", 0)
            except Exception as e:
                logger.error(f"Error calculating scorecard for application: {e}")

        # Status logging logic
        if self.pk:
            try:
                old_instance = Application.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    ApplicationStatusLog.objects.create(
                        tenant=self.tenant,
                        application=self,
                        old_status=old_instance.status,
                        new_status=self.status,
                    )
            except Application.DoesNotExist:
                pass

        super().save(*args, **kwargs)
        
        if is_new:
            logger.info(
                f"New Application created: {self.application_id} for {self.candidate.full_name if self.candidate else 'Unknown'}"
            )
        else:
            logger.info(
                f"Application {self.application_id} status changed to {self.status}"
            )


class ApplicationStatusLog(TenantModel):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="logs"
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)


class WorkExperience(TenantModel):
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="experience"
    )
    company_name = models.CharField(max_length=255)
    tier = models.ForeignKey(CompanyTier, on_delete=models.PROTECT)
    size = models.ForeignKey(CompanySize, on_delete=models.PROTECT)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # Null means 'Present'

    # Grade mapping: Bonus for high seniority
    previous_grade = models.ForeignKey(
        "org.Grade", on_delete=models.SET_NULL, null=True
    )

    # Recruiter can override this
    manual_weight_override = models.FloatField(null=True, blank=True)
    calculated_weight = models.FloatField(editable=False, default=0)

    def calculate_tenure_years(self):
        end = self.end_date or datetime.date.today()
        diff = end - self.start_date
        return round(diff.days / 365.25, 2)

    def save(self, *args, **kwargs):
        # 1. Base Weight = Tier Weight * Size Weight
        base_weight = self.tier.weight * self.size.weight

        # 2. Tenure Factor
        tenure = self.calculate_tenure_years()

        # 3. Grade Bonus (e.g., +20% for every grade level above entry)
        grade_bonus = 1.0
        if self.previous_grade:
            grade_bonus += (
                self.previous_grade.level * 0.1
            )  # Assuming Grade has a 'level' int

        # 4. Final Calculation
        if self.manual_weight_override is not None:
            self.calculated_weight = self.manual_weight_override
        else:
            self.calculated_weight = (base_weight * tenure) * grade_bonus

        super().save(*args, **kwargs)


class Education(TenantModel):
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="education"
    )
    institution = models.CharField(max_length=255)
    qualification = models.ForeignKey(QualificationLevel, on_delete=models.CASCADE)

    # Each row is its own degree (Cumulative logic)
    weight = models.FloatField(editable=False)

    def save(self, *args, **kwargs):
        # Simply take the weight from the level
        self.weight = float(self.qualification.weight)
        super().save(*args, **kwargs)




class JobShareLink(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE)
    shared_by = models.ForeignKey("employees.Employee", on_delete=models.CASCADE)
    expires_at = models.DateTimeField()
    view_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def is_valid(self):
        return self.is_active and timezone.now() < self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Default to 7 days expiry
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)


# ... Skills and Competency models stay similar but inherit from TenantModel ...
class Interview(TenantModel):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="interviews"
    )
    scheduled_at = models.DateTimeField()
    setup_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_interviews",
        help_text="Employee who scheduled/organized the interview",
    )
    interviewers = models.ManyToManyField(
        Employee,
        through="InterviewFeedback",
        related_name="assigned_interviews",
        help_text="Employees who actually conducted the interview",
    )
    location = models.CharField(max_length=50, default="Google Meet", choices=[
        ("Google Meet", "Google Meet"),
        ("Zoom", "Zoom"),
        ("In-Person", "In-Person")
    ])
    meeting_link = models.URLField(max_length=500, blank=True, null=True)

    def __str__(self):
        return (
            f"Interview: {self.application.candidate.full_name} @ {self.scheduled_at}"
        )


VERDICT_CHOICES = (
    ("PASS", "Pass"),
    ("FAIL", "Fail"),
    ("KIV", "Keep in View"),
)


class InterviewFeedback(TenantModel):
    interview = models.ForeignKey(
        Interview, on_delete=models.CASCADE, related_name="feedbacks"
    )
    interviewer = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="feedbacks"
    )
    notes = models.TextField(blank=True)
    rating = models.PositiveIntegerField(null=True, blank=True)  # optional score
    verdict = models.CharField(
        max_length=10, choices=VERDICT_CHOICES, null=True, blank=True
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "interview",
            "interviewer",
        )  # one feedback per interviewer per interview

    def __str__(self):
        return f"{self.interviewer} feedback for {self.interview}"


class Offer(TenantModel):
    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, related_name="offer"
    )
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=(
            ("PENDING", "Pending"),
            ("ACCEPTED", "Accepted"),
            ("DECLINED", "Declined"),
        ),
        default="PENDING",
    )
    offer_letter = models.FileField(
        upload_to=tenant_directory_path, null=True, blank=True
    )
    acceptance_letter = models.FileField(
        upload_to=tenant_directory_path, null=True, blank=True
    )

    def clean(self):
        if self.status == "ACCEPTED" and not self.acceptance_letter:
            raise ValidationError(
                "Acceptance letter is required for 'ACCEPTED' status."
            )

    def save(self, *args, **kwargs):
        # Detect status change to ACCEPTED
        is_accepting = False
        if self.pk:
            old_instance = Offer.objects.get(pk=self.pk)
            if old_instance.status != "ACCEPTED" and self.status == "ACCEPTED":
                is_accepting = True

        super().save(*args, **kwargs)

        if is_accepting:
            # Trigger the conversion service we discussed
            from ats.services.onboarding_services import HiringService

            HiringService.convert_candidate_to_employee(self.application.application_id)

            logger.info(
                f"[AUTOMATION] Candidate {self.application.candidate.full_name} accepted offer. Employee profile created."
            )


class OnboardingTemplate(TenantModel):
    """
    Standardized onboarding sets (e.g., 'Standard HQ Onboarding', 'Remote Engineer Kit').
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"


class OnboardingTaskTemplate(TenantModel):
    """
    Reusable tasks defined within a template.
    """

    template = models.ForeignKey(
        OnboardingTemplate, on_delete=models.CASCADE, related_name="task_templates"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    required_days = models.PositiveIntegerField(
        default=7, help_text="Days after start date to complete"
    )

    def __str__(self):
        return self.title


class OnboardingRequirement(TenantModel):
    """
    Defines what needs to be done (e.g., 'Upload Passport', 'Sign Data Policy').
    This is the 'Template' for the task.
    """

    REQUIREMENT_TYPES = [
        ("DOCUMENT", "File Upload"),
        ("ACKNOWLEDGEMENT", "Policy Sign-off"),
        ("DATA_ENTRY", "Profile Completion"),
        ("HARDWARE", "IT Provisioning"),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField()
    req_type = models.CharField(max_length=20, choices=REQUIREMENT_TYPES)
    # If it's a policy, link to the Document/Memo model
    linked_document = models.ForeignKey(
        WorkflowDocument, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_mandatory = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class OnboardingPlan(TenantModel):
    """
    The orchestrator. Links a Candidate from ATS to their new Employee profile.
    """

    STATUS_CHOICES = [
        ("NOT_STARTED", "Not Started"),
        ("IN_PROGRESS", "In Progress"),
        ("leave_application", "Orientation Phase"),  # Your custom state
        ("COMPLETED", "Completed"),
    ]

    application = models.OneToOneField(
        "ats.Application", on_delete=models.CASCADE, related_name="onboarding_plan"
    )
    # Once they start, they get an Employee profile
    employee = models.OneToOneField(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        related_name="onboarding_plan",
    )
    mentor = models.ForeignKey(
        "employees.Employee", on_delete=models.SET_NULL, null=True, blank=True
    )

    start_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="NOT_STARTED"
    )
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # The Workflow instance that tracks the OVERALL onboarding process
    workflow_instance = models.ForeignKey(
        WorkflowInstance, on_delete=models.SET_NULL, null=True
    )

    # Inside OnboardingPlan.update_progress
    def update_progress(self):
        total = self.tasks.count()
        if total > 0:
            completed = self.tasks.filter(is_completed=True).count()
            self.progress = (completed / total) * 100

            if self.progress == 100:
                self.status = "COMPLETED"
                self.finalize_payroll_setup()  # Trigger Payroll Automation
            self.save()

    def finalize_payroll_setup(self):
        """
        World-class logic: Automatically stage the new hire for payroll.
        Uses the salary from the accepted Offer.
        """
        from payroll.models import PayrollEntry
        from django.utils import timezone

        # 1. Fetch the agreed salary from the accepted offer
        offer = self.application.offer

        # 2. Mark Employee as 'Active'
        self.employee.work_status = "A"
        self.employee.save()

        logger.info(
            f"[PAYROLL_INTEGRATION] Employee {self.employee.first_name} {self.employee.last_name} is now PAY-READY. "
            f"Base Salary: {offer.salary} | Tenant: {self.tenant.code}"
        )


class OnboardingTask(TenantModel):
    """
    The Single Source of Truth for a specific onboarding action.
    """

    plan = models.ForeignKey(
        OnboardingPlan, on_delete=models.CASCADE, related_name="tasks"
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="assigned_onboarding_tasks",
    )

    # Template Data
    requirement = models.ForeignKey(OnboardingRequirement, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, help_text="Defaults to requirement name")

    # Workflow Linking
    stage = models.ForeignKey(
        WorkflowStage, on_delete=models.SET_NULL, null=True, blank=True
    )
    due_date = models.DateField()

    # Execution Data
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    uploaded_file = models.FileField(
        upload_to=tenant_directory_path, null=True, blank=True
    )
    signature_log = models.JSONField(
        null=True, blank=True, help_text="Stores IP and Timestamp for signatures"
    )

    class Meta:
        unique_together = ("employee", "requirement")

    def save(self, *args, **kwargs):
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()

        super().save(*args, **kwargs)
        # Auto-update the parent plan's progress bar
        if self.plan:
            self.plan.update_progress()
