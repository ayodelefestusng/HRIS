from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone
from employees.models import Employee
from talent.models import Skill


class Course(models.Model):
    """
    Represents a learning course offered to employees.
    Example: 'Python Basics', 'Leadership Training'.
    """
    title = models.CharField(max_length=200)
    description = models.TextField()
    skills = models.ManyToManyField(Skill, related_name="courses", blank=True)
    duration_hours = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TrainingSession(models.Model):
    """
    A scheduled instance of a course.
    Example: 'Python Basics - January 2026 Cohort'.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    start_date = models.DateField()
    end_date = models.DateField()
    trainer = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="training_sessions")
    location = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.course.title} ({self.start_date} - {self.end_date})"


class Enrollment(models.Model):
    """
    Links an employee to a training session.
    Tracks participation and completion status.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="enrollments")
    session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(default=timezone.now)
    completed = models.BooleanField(default=False)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.employee} enrolled in {self.session}"


class Certification(models.Model):
    """
    Represents a certification earned by an employee.
    Example: 'AWS Certified Solutions Architect'.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(max_length=200)
    issued_by = models.CharField(max_length=200, blank=True)
    issue_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee} - {self.name}"


class SkillMatrix(models.Model):
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