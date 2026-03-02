from django.db import models

# Create your models here.
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model


User = get_user_model()


from django.db import models


# org/models.py
from django.db import models
from .managers import TenantManager

class Tenant(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10, unique=True, help_text="Short unique code for the tenant (e.g., MSFT)")
    subdomain = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"



class TenantModel(models.Model):
    tenant = models.ForeignKey('org.Tenant', on_delete=models.CASCADE)
    
    # Use the custom manager
    objects = TenantManager()
    # Keep the original manager for cases where you NEED to see all data
    all_objects = models.Manager() 

    class Meta:
        abstract = True



class Country(TenantModel):
    """
    Represents a country where the organization operates.
    Example: Nigeria, Ghana, Kenya.
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


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
        ordering = ['name']
        unique_together = ('name', 'country')


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
        ordering = ['name']
        unique_together = ('name', 'state')


class Location(TenantModel):
    """
    Represents a physical or organizational location where jobs can be based.
    Example: Lagos Office, Abuja Branch, Remote.
    """
    location_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150, unique=True)
    address = models.CharField(max_length=255, blank=True)
    town = models.ForeignKey(Town, on_delete=models.CASCADE)
    head = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_locations",
        help_text="Employee who is the head of this location",
    )

    def __str__(self):
        return f"{self.name} ({self.location_id})"

    class Meta:
        ordering = ['name']
    

class Grade(TenantModel):
    """
    Represents a job grade or rank in the organization.
    Example: Manager (Level 10), Senior Manager (Level 11).
    """
    name = models.CharField(max_length=150, unique=True)   # e.g. "Manager"
    level = models.PositiveIntegerField(unique=True)       # e.g. 10

    # Core entitlements
    leave_days = models.PositiveIntegerField(default=0, help_text="Number of leave days per year")
    basic_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["level"]
        unique_together = ("name", "level")

    def __str__(self):
        return f"{self.name} (Level {self.level})"


class Department(TenantModel):
    name = models.CharField(max_length=100, unique=True)
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        related_name="departments", null=True
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
        Department,
        on_delete=models.SET_NULL,
        related_name="units", null=True
    )

    class Meta:
        unique_together = ("name", "department")

    def __str__(self):
        return f"{self.department.name} → {self.name}"


class OrgUnit(TenantModel):
    """
    Represents an organizational unit (e.g., Finance, HR, Payroll).
    Supports hierarchy via parent-child relationships and materialized paths.
    Each OrgUnit can be tied to a specific Location for easier querying.
    """

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)

    # Link to Location
    location = models.ForeignKey(
        "Location",
        on_delete=models.CASCADE,
        related_name="org_units",
        help_text="Physical or organizational location where this unit is based"
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children"
    )

    # Materialized path for fast tree queries
    path = models.CharField(max_length=500, editable=False)
    depth = models.PositiveIntegerField(default=0, editable=False)

    # KPIs
    cost_center = models.CharField(max_length=50, blank=True, null=True)
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    headcount_limit = models.PositiveIntegerField(default=0)

    sort_order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["path", "sort_order"]
        indexes = [
            models.Index(fields=["path"]),
            models.Index(fields=["depth"]),
            models.Index(fields=["parent", "sort_order"]),  # ✅ composite index for sibling ordering
        ]



    def __str__(self):
        return f"{self.name} (Level {self.depth})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.parent:
            self.path = f"{self.parent.path}{self.id}/"
            self.depth = self.parent.depth + 1
        else:
            self.path = f"{self.id}/"
            self.depth = 0
        super().save(update_fields=["path", "depth"])



class OrgUnitRole(TenantModel):
    """
    Defines a role within an OrgUnit (Head, Deputy, Member).
    Each OrgUnit can have multiple members but only one Head.
    """
    ROLE_CHOICES = [
        ("HEAD", "Head"),
        ("DEPUTY", "Deputy Head"),
        ("MEMBER", "Member"),
    ]

   

    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, related_name="roles")
    # employee = models.ForeignKey("employees.Employee", on_delete=models.SET_NULL, null=True, blank=True)
    role_type = models.CharField(max_length=20, choices=ROLE_CHOICES)
    

    # Authority chain
    AUTHORITY_CHOICES = [
        ("REVIEWER", "Reviewer"),
        ("CONCURRENCE", "Concurrence Approval"),
        ("APPROVER", "Approver"),
        ("SNMGT", "Senior Management"),
        ("EXCO", "Executive Committee"),
        ("BOARD", "Board"),
    ]
    authority_level = models.CharField(max_length=20, choices=AUTHORITY_CHOICES, default="REVIEWER")

    relieve = models.ForeignKey("employees.Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="relieve_roles")

    class Meta:
        unique_together = ("org_unit", "role_type")

    def __str__(self):
        return f"{self.org_unit.name} → {self.role_type} ({self.status})"




class OrgWorkflowRoute(TenantModel):
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE)
    workflow_name = models.CharField(max_length=150)
    approver_role = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.workflow_name} → {self.approver_role} ({self.org_unit})"

STATUS_CHOICES = [
        ("ACTING", "Acting"),
        ("SUBSTANTIVE", "Substantive"),
        ("VACANT", "Vacant"),
    ]

class RoleOfficerInCharge(TenantModel):
    """
    Defines a logical role profile with competencies and skills.
    Example: Cash Office Head, Payroll Officer.
    """
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    org_unit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE)

    officer_in_charge = models.ForeignKey("employees.Employee", on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SUBSTANTIVE")
    def __str__(self):
        return self.name


class RoleCompetencyRequirement(TenantModel):
    """
    Defines competency requirements for a role.
    """
    role = models.ForeignKey(OrgUnitRole, on_delete=models.CASCADE, related_name="competencies")
    competency = models.ForeignKey("talent.Competency", on_delete=models.CASCADE)
    required_level = models.PositiveSmallIntegerField(default=3)
    weight = models.PositiveSmallIntegerField(default=3)        

    class Meta:
        unique_together = ("role", "competency")


class RoleSkillRequirement(TenantModel):
    """
    Defines skill requirements for a role.
    """
    role = models.ForeignKey(OrgUnitRole, on_delete=models.CASCADE, related_name="skills")
    skill_name = models.ForeignKey("talent.Skill", on_delete=models.CASCADE)
    required_level = models.PositiveSmallIntegerField(default=3)

    class Meta:
        unique_together = ("role", "skill_name")
        
        
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
