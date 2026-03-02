from email.mime import application
import uuid
from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from employees.models import Employee,EmploymentStatus,Department, Unit
from org.models import Location

from talent.models import Skill,Competency


User = get_user_model()




class JobPosting(models.Model):
    """
    Represents an open job posting in the ATS.
    """

    STATUS_CHOICES = (
        ("OPEN", "Open"),
        ("CLOSED", "Closed"),
        ("DRAFT", "Draft"),
    )

    title = models.CharField(max_length=200)
    # department = models.ForeignKey(
    #     Department,
    #     on_delete=models.PROTECT,
    #     related_name="job_postings"
    # )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="job_postings",
        null=True,
        blank=True
    )
    description = models.TextField()
    requirements = models.TextField()

    # ✅ Many-to-many relationship to Location
    locations = models.ManyToManyField(
        Location,
        related_name="job_postings",
        help_text="Job can be available at multiple locations"
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OPEN")
    employment_type = models.CharField(
        max_length=2,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.FULL_TIME
    )

    created_at = models.DateTimeField(auto_now_add=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} {' / ' + self.unit.name if self.unit else ''})"
    
    
class Applicant(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True, null=True)
    resume = models.FileField(upload_to="resumes/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Application(models.Model):
    STATUS_CHOICES = choices=[
            ("APPLIED", "Applied"),
            ("INTERVIEW", "Interview"),
            ("OFFER", "Offer"),
            ("HIRED", "Hired"),
            ("REJECTED", "Rejected"),
        ]

    application_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE, related_name="applications")
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="APPLIED")
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.applicant.full_name} → {self.job_posting.title}"

  
class Candidate(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="applicationID")
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.full_name


class CandidateSkillProfile(models.Model):
    candidate = models.ForeignKey(Candidate,on_delete=models.CASCADE,related_name="skill_profiles",)
    skill = models.ForeignKey(Skill,on_delete=models.CASCADE,related_name="candidate_skill_profiles",)
    level = models.PositiveSmallIntegerField(default=1,help_text="Inferred or assessed level (1–5).",)

    class Meta:
        unique_together = ("candidate", "skill")

    def __str__(self):
        return f"{self.candidate} → {self.skill} (lvl={self.level})"



class CandidateCompetencyProfile(models.Model):
    candidate = models.ForeignKey(
        Candidate,on_delete=models.CASCADE,related_name="competency_profiles",)
    competency = models.ForeignKey( Competency,on_delete=models.CASCADE,related_name="candidate_competency_profiles",)
    level = models.PositiveSmallIntegerField(default=1,help_text="Competency level (1–5).", )

    class Meta:
        unique_together = ("candidate", "competency")

    def __str__(self):
        return f"{self.candidate} → {self.competency} (lvl={self.level})"






class Interview(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="interviews")
    scheduled_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Many-to-many relationship through InterviewFeedback
    interviewers = models.ManyToManyField( Employee,through="InterviewFeedback",related_name="interviews")

    def __str__(self):
        return f"Interview for {self.application} on {self.scheduled_at}"

VERDICT_CHOICES = (
        ("PASS", "Pass"),
        ("FAIL", "Fail"),
        ("KIV", "Keep in View"),
    )


class InterviewFeedback(models.Model):
    interview = models.ForeignKey( Interview, on_delete=models.CASCADE, related_name="feedbacks")
    interviewer = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="feedbacks")
    notes = models.TextField(blank=True)
    rating = models.PositiveIntegerField(null=True, blank=True)  # optional score
    verdict = models.CharField(max_length=10, choices=VERDICT_CHOICES, null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("interview", "interviewer")  # one feedback per interviewer per interview

    def __str__(self):
        return f"{self.interviewer} feedback for {self.interview}"


from django.db import models
from django.core.exceptions import ValidationError

class Offer(models.Model):
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="offer"
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

    # New fields
    offer_letter = models.FileField(
        upload_to="offers/letters/",
        null=True,
        blank=True,
        help_text="Upload the official offer letter file"
    )
    acceptance_letter = models.FileField(
        upload_to="offers/acceptances/",
        null=True,
        blank=True,
        help_text="Upload the acceptance letter file (required if status=ACCEPTED)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """
        Custom validation:
        If status is ACCEPTED, acceptance_letter must be provided.
        """
        if self.status == "ACCEPTED" and not self.acceptance_letter:
            raise ValidationError("Acceptance letter is required when status is ACCEPTED.")

    def __str__(self):
        return f"Offer → {self.application}"
    
  