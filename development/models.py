from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone
from employees.models import Employee


import logging
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from org.models import TenantModel
from employees.models import Employee

from performance.models import Appraisal
logger = logging.getLogger(__name__)

class Competency(TenantModel):
    """
    Broad capability (e.g. 'Data Analysis', 'Leadership').
    """
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Skill(TenantModel):
    """
    Atomic skill (e.g. 'Python', 'Public Speaking').
    """
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name



class CompetencySkill(TenantModel):
    """
    Links a competency to one or more skills.
    """
    competency = models.ForeignKey(
        Competency,
        on_delete=models.CASCADE,
        related_name="competency_skills",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="skill_competencies",
    )
    

    class Meta:
        unique_together = ("competency", "skill")

    def __str__(self):
        return f"{self.competency} → {self.skill}"


class EmployeeRoleFit(TenantModel):
    """
    Cached fit score of an employee to a role.
    """
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="role_fits",
    )
    role = models.ForeignKey(
       "org.JobRole",
        on_delete=models.CASCADE,
        related_name="employee_fits",
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("employee", "role")

    def __str__(self):
        return f"{self.employee} vs {self.role}: {self.score}"
    

class Course(TenantModel):
    """
    World-class: Added 'Category' and 'Mandatory' flags for compliance training.
    """
    CATEGORY_CHOICES = [
        ("TECH", "Technical"),
        ("SOFT", "Soft Skills"),
        ("COMP", "Compliance/Legal"),
        ("LEAD", "Leadership"),
    ]
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default="TECH")
    description = models.TextField()
    skills_taught = models.ManyToManyField(Skill, related_name="courses", blank=True)
    duration_hours = models.PositiveIntegerField(default=0)
    is_mandatory = models.BooleanField(default=False, help_text="Is this required for all employees?")
    
    class Meta:
        unique_together = ("tenant", "title")

    def __str__(self):
        return self.title

class TrainingSession(TenantModel):
    """
    Tracks cohorts. Added 'Capacity' to prevent over-enrollment.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    start_date = models.DateField()
    end_date = models.DateField()
    capacity = models.PositiveIntegerField(default=20)
    trainer = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.CharField(max_length=200, help_text="Physical room or Meeting Link")

    def __str__(self):
        return f"{self.course.title} Cohort ({self.start_date})"

class Enrollment(TenantModel):
    """
    Tracks the employee's journey. Added a 'Status' state machine.
    """
    STATUS_CHOICES = [
        ("ENR", "Enrolled"),
        ("IPG", "In Progress"),
        ("COM", "Completed"),
        ("FAL", "Failed/Dropped"),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="enrollments")
    session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default="ENR")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback_rating = models.PositiveIntegerField(null=True, blank=True, validators=[MaxValueValidator(5)])
    certificate_file = models.FileField(upload_to="enrol_certs/", null=True, blank=True)
    class Meta:
        unique_together = ("employee", "session", "tenant")

    def save(self, *args, **kwargs):
        # Auto-update Skill Matrix on completion
        is_new_completion = False
        if self.pk:
            old_status = Enrollment.objects.get(pk=self.pk).status
            if old_status != "COM" and self.status == "COM":
                is_new_completion = True
        
        super().save(*args, **kwargs)
        
        if is_new_completion:
            self.update_employee_skills()

    def update_employee_skills(self):
        """Logic to boost skill levels in SkillMatrix upon course completion."""
        for skill in self.session.course.skills_taught.all():
            matrix, created = SkillMatrix.objects.get_or_create(
                employee=self.employee, skill=skill, tenant=self.tenant
            )
            if matrix.level < 5:
                matrix.level += 1
                matrix.save()
                logger.info(f"Skill Upgraded: {self.employee} now level {matrix.level} in {skill.name}")

class Certification(TenantModel):
    """
    Tracks professional credentials. Added 'is_expired' logic.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(max_length=200)
    issued_by = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    certificate_file = models.FileField(upload_to="certs/", null=True, blank=True)

    @property
    def is_expired(self):
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False

    def __str__(self):
        return f"{self.name} - {self.employee.full_name}"



class SkillMatrix(TenantModel):
    """
    Tracks an employee’s skill levels across defined skills.
    Useful for competency mapping and gap analysis.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="skill_matrix")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="skill_matrix_entries")
    level = models.PositiveIntegerField(default=1, help_text="1=Beginner, 5=Expert")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("employee", "skill")

    def __str__(self):
        return f"{self.employee} - {self.skill.name} ({self.level})"
    
    
# development/models.py (Additions)

class GradeRequirement(TenantModel):
    """
    Defines the 'Bar' an employee must cross to reach or maintain a Grade.
    Example: To be a 'Senior Manager', you need 'Leadership' Level 4.
    """
    grade = models.ForeignKey("org.Grade", on_delete=models.CASCADE, related_name="requirements")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    minimum_level = models.PositiveIntegerField(
        default=3, 
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Required skill level (1-5)"
    )
    mandatory_courses = models.ManyToManyField(Course, blank=True, help_text="Courses that must be completed.")

    class Meta:
        unique_together = ("grade", "skill", "tenant")

    def __str__(self):
        return f"{self.grade.name} Requirement: {self.skill.name} (Lvl {self.minimum_level})"
    
    
    

## Reducntat
class EmployeeSkillProfile(TenantModel):
    """
    Tracks an employee's self-assessed or manager-assessed skill level.
    """
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="skill_profiles",
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="employee_skills",
    )
    level = models.PositiveSmallIntegerField(
        default=1,
        help_text="Proficiency level (1–10).",
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    source = models.CharField(
        max_length=50,
        default="self",
        help_text="Source of rating: self, manager, assessment, system",
    )
    comment = models.TextField(
        blank=True,
        null=True,
        help_text="Comment on the rating.",
    )

    class Meta:
        unique_together = ("employee", "skill")

    def __str__(self):
        return f"{self.employee} → {self.skill} (lvl={self.level})"
