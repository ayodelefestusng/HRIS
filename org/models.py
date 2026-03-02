import logging
import os

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Apply to Certification
# certificate_file = models.FileField(upload_to=development_directory_path, null=True, blank=True)
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models



from .managers import TenantManager
from django.db.models import Q  
logger = logging.getLogger(__name__)
User = get_user_model()


def tenant_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/tenant_<id>/<model_name>/filename
    # For Tenant model itself, use instance.id; for other models, use instance.tenant.id
    model_name = instance.__class__.__name__.lower()
    tenant_id = instance.id if model_name == "tenant" else instance.tenant.id
    return f"tenant_{tenant_id}/{model_name}/{filename}"


def expense_directory_path(instance, filename):
    # Files stored as: tenant_1/payroll/reimbursement/2026/01/filename.jpg
    date_path = timezone.now().strftime("%Y/%m")
    return f"tenant_{instance.tenant.id}/payroll/{instance._meta.model_name}/{date_path}/{filename}"


def development_directory_path(instance, filename):
    # Files stored as: tenant_1/development/certification/filename.pdf
    return f"tenant_{instance.tenant.id}/development/{instance._meta.model_name}/{filename}"



class Tenant(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short unique code for the tenant (e.g., MSFT)",
    )
    subdomain = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    brand_name = models.CharField(
        max_length=210,
        default="Dignity",
        help_text="Brand name , e.g., Dignity",
    )
    # Branding Fields
    logo = models.ImageField(
        upload_to=tenant_directory_path,
        null=True,
        blank=True,
        help_text="Primary logo for the tenant (displayed in header)",
    )
    favicon = models.ImageField(
        upload_to=tenant_directory_path,
        null=True,
        blank=True,
        help_text="Tenant-specific favicon",
    )
    primary_color = models.CharField(
        max_length=7,
        default="#4f46e5",
        help_text="Brand primary color (Hex), e.g., #4f46e5",
    )
    secondary_color = models.CharField(
        max_length=7,
        default="#6366f1",
        help_text="Brand secondary color (Hex), e.g., #6366f1",
    )
    font_family = models.CharField(
        max_length=255,
        default="'Inter', sans-serif",
        help_text="CSS Font family for the tenant",
    )
    custom_css = models.TextField(
        blank=True,
        help_text="Custom CSS overrides for this tenant",
    )

    def __str__(self):
        return f"{self.name} ({self.code})"


class TenantModel(models.Model):
    # tenant = models.ForeignKey('org.Tenant', on_delete=models.CASCADE)
    tenant = models.ForeignKey(
        "org.Tenant", on_delete=models.CASCADE, null=True, blank=True
    )

    # Use the custom manager
    objects = TenantManager()
    # Keep the original manager for cases where you NEED to see all data
    all_objects = models.Manager()

    class Meta:
        abstract = True
# https://copilot.microsoft.com/shares/guBVcRj7GYsaeDafD1M61
# https://www.youtube.com/watch?v=bnKnT46s-PI
class TaggedItem(TenantModel):
    tag = models.SlugField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    
    def __str__(self):
        return self.tag
    def save(self, *args, **kwargs):
        if self.content_object is not None and hasattr(self.content_object, "tenant"):
            self.tenant = self.content_object.tenant
        super().save(*args, **kwargs)
    def get_related_objectsv1(self):
        related = {}
        # Example: documents attached to this application
        related["documents"] = list(self.taggeditem_set.all())
        # Example: interviews scheduled for this application
        related["interviews"] = list(self.interviews.all())
        return related
    # https://copilot.microsoft.com/shares/guBVcRj7GYsaeDafD1M61
    def get_related_objects(self):
        KLass = self.content_type.model_class()
        return KLass.objects.filter(id=self.object_id).first()
    @property
    def related_objects(self):
        return self.get_related_objects()
    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

class Country(TenantModel):
    """
    Represents a country where the organization operates.
    Example: Nigeria, Ghana, Kenya.
    """

    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class State(TenantModel):
    """
    Represents a state/region within a country.
    Example: Lagos State, Abuja FCT.
    """

    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}, {self.country.name}"

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "country")
class Town(TenantModel):
    """
    Represents a town/city within a state.
    Example: Ikeja, Victoria Island.
    """

    name = models.CharField(max_length=100)
    state = models.ForeignKey(State, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}, {self.state.name}"

    class Meta:
        ordering = ["name"]
        unique_together = ("tenant", "name")

from django.db import models
from django.utils import timezone

class LinkedInIntegration(TenantModel):
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    redirect_uri = models.URLField()
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    def is_token_valid(self):
        return self.expires_at and timezone.now() < self.expires_at


class GoogleMeetIntegration(TenantModel):
    CLIENT_ID = models.CharField(max_length=255)
    CLIENT_SECRET = models.CharField(max_length=255)
    REDIRECT_URI = models.URLField()
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    def is_token_valid(self):
        return self.expires_at and timezone.now() < self.expires_at
  

class Location(TenantModel):
    """
    Represents a physical or organizational location where jobs can be based.
    Example: Lagos Office, Abuja Branch, Remote.
    """

    location_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150, unique=True)
    address = models.CharField(max_length=255, blank=True)
    town = models.ForeignKey(Town, on_delete=models.CASCADE)

    # 📸 Add photo field
    photo = models.ImageField(
        upload_to=tenant_directory_path,
        null=True,
        blank=True,
        help_text="Optional photo representing this organizational unit",
    )
    # 🌍 Add longitude and latitude
    latitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Latitude coordinate of the organizational unit",
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Longitude coordinate of the organizational unit",
    )

    # head = models.ForeignKey(
    #     "employees.Employee",
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name="headed_locations",
    #     help_text="Employee who is the head of this location",
    # )

    def __str__(self):
        return f"{self.name} ({self.location_id})"

    class Meta:
        ordering = ["name"]

class CompanyTier(TenantModel):
    """e.g., Multinational (10), National (7), Local (3)"""
    name = models.CharField(max_length=100)
    weight = models.PositiveIntegerField(default=1,help_text="e.g., Multinational (10), National (7), Local (3)")

    class Meta:
        unique_together = ("tenant", "name")
        
    def clean(self):
        super().clean()
        if self.weight < 1:
            raise ValidationError("Weight must be at least 1.")
        
        # Check for gaps in weight within the same tenant
        existing_weights = CompanyTier.objects.filter(
            tenant=self.tenant
        ).exclude(pk=self.pk).values_list('weight', flat=True)

        if existing_weights:
            max_weight = max(existing_weights)
            if self.weight > max_weight + 1:
                raise ValidationError(f"Weight is not consecutive. The next weight should be {max_weight + 1}.")

      
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):  
        return f"{self.name}, {self.weight}"
    

class CompanySize(TenantModel):
    """e.g., Large (3), Mid (2), Small (1)"""
    name = models.CharField(max_length=100)
    weight = models.PositiveIntegerField(default=1,help_text="e.g., Large (3), Mid (2), Small (1)")
    
    def clean(self):
        super().clean()
        if self.weight < 1:
            raise ValidationError("Weight must be at least 1.")
        
        # Check for gaps in weight within the same tenant
        existing_weights = CompanySize.objects.filter(
            tenant=self.tenant
        ).exclude(pk=self.pk).values_list('weight', flat=True)

        if existing_weights:
            max_weight = max(existing_weights)
            if self.weight > max_weight + 1:
                raise ValidationError(f"Weight is not consecutive. The next weight should be {max_weight + 1}.")
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
      
    def __str__(self):
        return f"{self.name}, {self.weight}"

    class Meta:
        ordering = ["name"]
        unique_together = ("tenant", "name")

class QualificationLevel(TenantModel):
    """e.g., PHD (10), Masters (8), Graduate (6)"""
    name = models.CharField(max_length=100, help_text="e.g., PHD (10), Masters (8), Graduate (6)")
    weight = models.PositiveIntegerField(default=1,help_text="e.g., PHD (10), Masters (8), Graduate (6)")
    
    def __str__(self):
        return f"{self.name}, {self.weight}"

    class Meta:
        ordering = ["name"]
        unique_together = ("tenant", "name")



class PyramidGroup(TenantModel):
    """
    Represents a job grade or rank in the organization.
    Example: Manager (Level 10), Senior Manager (Level 11).
    """

    name = models.CharField(max_length=150, unique=True)  # e.g. "Top"
    level = models.PositiveIntegerField(unique=True)  # e.g. 3

    class Meta:
        ordering = ["level"]
        unique_together = ("name", "level")
    def clean(self):
        super().clean()
        if self.level < 1:
            raise ValidationError("Level must be at least 1.")
        
        # Check for gaps in level within the same tenant
        existing_levels = PyramidGroup.objects.filter(
            tenant=self.tenant
        ).exclude(pk=self.pk).values_list('level', flat=True)

        if existing_levels:
            max_level = max(existing_levels )
            if self.level > max_level + 1:
                raise ValidationError(f"Level is not consecutive. The next level should be {max_level + 1}.")
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
      
    def __str__(self):
        return f"{self.name} (Level {self.level})"


class Grade(TenantModel):
    """
    Represents a job grade or rank in the organization.
    Example: Manager (Level 10), Senior Manager (Level 11).
    """

    name = models.CharField(max_length=150, unique=True)  # e.g. "Manager"
    level = models.PositiveIntegerField(unique=True)  # e.g. 10
    pyramid = models.ForeignKey(
        PyramidGroup,
        on_delete=models.SET_NULL,  # instead of CASCADE
        related_name="pyramid",
        null=True,  # allow NULL in database
        blank=True,  # allow empty in forms/admin
    )

    # Core entitlements
    annual_leave_days = models.PositiveIntegerField(
        default=0, help_text="Number of leave days per year"
    )
    basic_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["level"]
        unique_together = ("name", "level")
   
   
   
    def clean(self):
        super().clean()
        if self.level < 1:
            raise ValidationError("Level must be at least 1.")
        
        # Check for gaps in level within the same tenant
        existing_levels = Grade.objects.filter(
            tenant=self.tenant
        ).exclude(pk=self.pk).values_list('level', flat=True)

        if existing_levels:
            max_level = max(existing_levels )
            if self.level > max_level + 1:
                raise ValidationError(f"Level is not consecutive. The next level should be {max_level + 1}.")
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    
    
    def __str__(self):
        return f"{self.name} (Level {self.level})"


class OrgUnit(TenantModel):
    name = models.CharField(max_length=150)
    # Optimized: Code is unique within the company only
    code = models.CharField(max_length=50)

    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="org_units"
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    path = models.CharField(max_length=500, editable=False, db_index=True)
    depth = models.PositiveIntegerField(default=0, editable=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["path", "code"]
        # unique_together = ('tenant', 'code') # Allows 'FIN' in multiple companies
        # ... your existing indexes ...

    def save(self, *args, **kwargs):
        # 1. First save to ensure we have an ID
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # 2. Update path/depth based on parent
        old_path = self.path
        if self.parent:
            self.path = f"{self.parent.path}{self.pk}/"
            self.depth = self.parent.depth + 1
        else:
            self.path = f"{self.pk}/"
            self.depth = 0

        # 3. Only save again if path actually changed to avoid infinite loops
        if old_path != self.path:
            super().save(update_fields=["path", "depth"])

        if is_new:
            logger.info(f"OrgUnit {self.name} created for Tenant {self.tenant.code}")

    def __str__(self):
        return f"{self.name} → {self.location} "


STATUS_CHOICES = [
    ("ACTING", "Acting"),
    ("SUBSTANTIVE", "Substantive"),
    ("VACANT", "Vacant"),
]
ROLE_CHOICES = [
    ("HEAD", "Head"),
    ("DEPUTY", "Deputy Head"),
    ("MEMBER", "Member"),
]

class JobTitle(TenantModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    class Meta:
        unique_together = ("tenant", "name")


class JobRole(TenantModel):
    """
    Defines a role within an OrgUnit (Head, Deputy, Member).
    Each OrgUnit can have multiple members but only one Head.
    """

    org_unit = models.ForeignKey(
        OrgUnit, on_delete=models.CASCADE, related_name="roles"
    )
    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.SET_NULL, null=True, blank=True,related_name="roles" 
    )
    role_type = models.CharField(max_length=20, choices=ROLE_CHOICES)
    # designation = models.CharField(max_length=50)
    job_title = models.ForeignKey(JobTitle, on_delete=models.SET_NULL, null=True, blank=True,related_name="roles") # NEW
    is_deleted = models.BooleanField(default=False) 
    vacant = models.BooleanField(default=False)
    
    min_years_experience = models.PositiveIntegerField(default=0)
    # Selection of multiple allowed qualifications (e.g., Graduate AND Certification)
    required_qualifications = models.ManyToManyField(QualificationLevel)
    # Authority chain
    AUTHORITY_CHOICES = [
        ("REVIEWER", "Reviewer"),
        ("CONCURRENCE", "Concurrence Approval"),
        ("APPROVER", "Approver"),
        ("SNMGT", "Senior Management"),
        ("EXCO", "Executive Committee"),
        ("BOARD", "Board"),
    ]
    authority_level = models.CharField(
        max_length=20, choices=AUTHORITY_CHOICES, default="REVIEWER"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="SUBSTANTIVE"
    )
    relieve = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="relieve_roles",
    )

    # class Meta:
    #     # unique_together = ("org_unit", "role_type")
    #     unique_together = ("org_unit", "employee")
    #     constraints = [
    #     models.UniqueConstraint(
    #         fields=["org_unit"],
    #         condition=Q(role_type="HEAD"),
    #         name="unique_head_per_orgunit"
    #     )
    # ]


    def clean(self):
        # Rule 1: Max of two Deputy Heads
        if self.role_type == "DEPUTY":
            deputies = JobRole.objects.filter(
                org_unit=self.org_unit, role_type="DEPUTY"
            ).exclude(pk=self.pk)
            if deputies.count() >= 2:
                raise ValidationError(
                    "An OrgUnit cannot have more than two Deputy Heads."
                )

        # Get Head grade level (if exists)
        head = JobRole.objects.filter(org_unit=self.org_unit, role_type="HEAD").first()
        head_level = (
            head.employee.grade.level
            if head and head.employee and head.employee.grade
            else None
        )

        # Rule 2: Deputy grade ≤ Head grade
        if self.role_type == "DEPUTY" and self.employee and head_level:
            if self.employee.grade.level > head_level:
                raise ValidationError(
                    "Deputy grade level cannot be higher than Head grade level."
                )

        # Rule 3: Member grade ≤ Deputy or Head grade
        if self.role_type == "MEMBER" and self.employee:
            deputies = JobRole.objects.filter(
                org_unit=self.org_unit, role_type="DEPUTY"
            )
            deputy_levels = [
                d.employee.grade.level
                for d in deputies
                if d.employee and d.employee.grade
            ]
            max_deputy_level = max(deputy_levels) if deputy_levels else None

            # Compare against Head or Deputy
            allowed_level = max(filter(None, [head_level, max_deputy_level]))
            if allowed_level and self.employee.grade.level > allowed_level:
                raise ValidationError(
                    "Member grade level cannot be higher than Deputy Head or Head grade level."
                )
    @property
    def is_vacant(self):
        return self.employee is None or self.status == "VACANT"
    
    def get_head(self):
        # Query the JobRole class for this specific unit
        return JobRole.objects.filter(org_unit=self.org_unit, role_type="HEAD").first()

    def get_deputies(self):
        return JobRole.objects.filter(org_unit=self.org_unit, role_type="DEPUTY")
    
    
    # def __str__(self):
    #     return f"{self.employee.first_name} {self.employee.last_name} - {self.job_title.name} ({self.role_type})" 
    def __str__(self):
        # return f"{self.employee.first_name} {self.employee.last_name} {self.role_type} {self.org_unit.name if self.org_unit else 'N/A'} {self.job_title.name if self.job_title else 'N/A'}  "
        return f"  {self.job_title.name if self.job_title else 'N/A'} {self.org_unit.name }  "

    def save(self, *args, **kwargs):
        if self.role_type == "HEAD":
            # Ensure only one HEAD per org_unit
            JobRole.objects.filter(org_unit=self.org_unit, role_type="HEAD").exclude(pk=self.pk).update(is_deleted=True)
        super().save(*args, **kwargs)


class RoleCompetencyRequirement(TenantModel):
    """
    Defines competency requirements for a role.
    """

    role = models.ForeignKey(
        JobRole, on_delete=models.CASCADE, related_name="competencies"
    )
    competency = models.ForeignKey("development.Competency", on_delete=models.CASCADE)
    required_level = models.PositiveSmallIntegerField(default=3)
    weight = models.PositiveSmallIntegerField(default=3)

    class Meta:
        unique_together = ("role", "competency")
    def __str__(self):
        # return f"{self.employee.first_name} {self.employee.last_name} {self.role_type} {self.org_unit.name if self.org_unit else 'N/A'} {self.job_title.name if self.job_title else 'N/A'}  "
        return f"  {self.role.org_unit.name if self.role else 'N/A'} : {self.role.job_title.name if self.role else 'N/A'}-{self.competency.name }  "

class RoleSkillRequirement(TenantModel):
    """
    Defines skill requirements for a role.
    """

    role = models.ForeignKey(JobRole, on_delete=models.CASCADE, related_name="skills")
    skill_name = models.ForeignKey("development.Skill", on_delete=models.CASCADE)
    required_level = models.PositiveSmallIntegerField(default=3)

    class Meta:
        unique_together = ("role", "skill_name")


class OrgWorkflowRoute(TenantModel):
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE)
    workflow_name = models.CharField(max_length=150)
    approver_role = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.workflow_name} → {self.approver_role} ({self.org_unit})"


class OrgUnitVersion(TenantModel):
    version = models.PositiveIntegerField()
    snapshot_date = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()

    class Meta:
        ordering = ["-version"]

    def __str__(self):
        return f"Version {self.version}"


class OrgSnapshot(TenantModel):
    captured_at = models.DateTimeField(auto_now_add=True)
    tree = models.JSONField()
    metrics = models.JSONField(default=dict)

    def __str__(self):
        return f"Snapshot {self.captured_at}"


class RoleOfficerInCharge(TenantModel):
    """
    Defines a logical role profile with competencies and skills.
    Example: Cash Office Head, Payroll Officer.
    """

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE)

    officer_in_charge = models.ForeignKey(
        "employees.Employee", on_delete=models.SET_NULL, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="SUBSTANTIVE"
    )

    def __str__(self):
        return self.name


class Department(TenantModel):
    name = models.CharField(max_length=100, unique=True)
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, related_name="departments", null=True
    )

    def __str__(self):
        return self.name


class Unit(TenantModel):
    """
    A Unit belongs to a Department.
    Example: HR → Recruitment Unit, Finance → Payroll Unit.
    """

    name = models.CharField(max_length=100)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, related_name="units", null=True
    )

    class Meta:
        unique_together = ("name", "department")

    def __str__(self):
        return f"{self.department.name} → {self.name}"
