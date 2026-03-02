import logging
import os
from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator, MaxValueValidator

from org.models import STATUS_CHOICES, TenantModel
from employees.models import Employee

from decimal import Decimal
logger = logging.getLogger(__name__)


STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("COMPLETED", "Completed"),
    ("ACTIVE", "Active"),
    ("INACTIVE", "Inactive"),
]
class AppraisalCycle(TenantModel):
    """Defines the period (e.g., 'Annual Review 2025', 'Q1 Review')."""
    name = models.CharField(max_length=100, help_text="Name of the period (e.g., 'Annual Review 2025').")
    is_active = models.BooleanField(default=True, help_text="Only one cycle should be active for a tenant at a time.")
    
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    

    def __str__(self):
        return f"{self.name} ({self.tenant.code})"


class PerformanceIndicator(TenantModel):
    """Key Performance Indicators assigned to employees."""
    # CATEGORY_CHOICES = [('KPI', 'Key Performance Indicator'), ('BEHAVIOR', 'Core Value')]
    CATEGORY_CHOICES = [('KPI', 'KPI'), ('COMP', 'Competency'), ('BEH', 'Behavior')]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="kpis")
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE)
    
    
    
    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES,
        help_text="KPIs are quantifiable; Behaviors are qualitative soft skills."
    )
    weight = models.PositiveIntegerField(help_text="Weight out of 100")
    description = models.TextField(blank=True)
    
    target_value = models.CharField(max_length=100, help_text="e.g., $1M Revenue or 95% Uptime")
    current_actual = models.CharField(max_length=100, blank=True)
    
    status = models.CharField(max_length=20, choices=[
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('ACHIEVED', 'Achieved'),
        ('EXCEEDED', 'Exceeded'),
        ('DROPPED', 'Dropped'),
    ], default='NOT_STARTED')
    
    class Meta:
        unique_together = ('tenant', 'title')
    def __str__(self):
        return f"{self.title} ({self.weight}%)"
    

class Appraisal(TenantModel):
    """The main appraisal document."""
    STATUS_CHOICES = [
        ("draft", "Self-Appraisal"),
        ("review", "Manager-Review"),
        ("moderation", "HR-Moderation"),
        ("completed", "Completed"),

        ("pending", "Pending"), 
        ("rejected_for_amendment", "Rejected for Amendment"), 
        ("approved", "Approved"), 
        ("rejected", "Rejected")
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="appraisals")
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE)
    manager = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name="managed_appraisals")
    
    # Scores (Usually 1-5 scale)
    kpi_score = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    competency_score = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    final_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    
    # Qualitative Feedback
    employee_comments = models.TextField(blank=True)
    manager_comments = models.TextField(blank=True)
    improvement_plan = models.TextField(blank=True)
    
    approval_status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="draft")
    final_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Automatically calculated weighted average of all ratings from indicators."
    )
    normalized_grade = models.CharField(max_length=2, blank=True, null=True) # A, B, C, D
    moderated_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    is_moderated = models.BooleanField(default=False)
    
    @property
    def is_high_performer(self):
        """Identifies top talent scoring 4.5 and above."""
        return self.final_score is not None and self.final_score >= 4.5

    @property
    def is_under_performer(self):
        """Identifies employees needing Improvement Plans (PIP)."""
        return self.final_score is not None and self.final_score < 2.5

    @property
    def get_status_display_color(self):
        """Helper for frontend UI colors."""
        colors = {
            'draft': 'gray',
            'review': 'blue',
            'moderation': 'orange', # Custom state
            'approved': 'green'
        }
        return colors.get(self.approval_status, 'black')
    
    def calculate_score(self):
        """
        World-class logic: Calculates score based on Indicator weights.
        Formula: Sum(Score * (Weight/100))
        """
    
        ratings = self.ratings.select_related('indicator').all()
        if not ratings:
            return 0
        total_weighted_score = 0
        total_weight_found = 0
        
        
        for r in ratings:
            # We use the manager_score for the official final result
            weight_decimal = r.indicator.weight / 100
            total_weighted_score += (r.manager_score * weight_decimal)
            total_weight_found += r.indicator.weight
        self.final_score = total_weighted_score
        # Logging the calculation for audit trails
        logger.info(
            f"[Tenant: {self.tenant.code}] Calculated score for {self.employee}: "
            f"{self.final_score} (Total weight accounted: {total_weight_found}%)"
        )
        # Use .update() to bypass the save() method and avoid RecursionError
        Appraisal.objects.filter(pk=self.pk).update(final_score=total_weighted_score)
        self.final_score = total_weighted_score # Update local instance memory
        logger.info(
            f"[Tenant: {self.tenant.code}] Calculated score for {self.employee}: "
            f"{self.final_score} (Total weight: {total_weight_found}%)"
        )
        return total_weighted_score
    
        # Inside Appraisal model save method
    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields and 'final_score' in update_fields and len(update_fields) == 1:
            return super().save(*args, **kwargs)
        if self.pk:
            # original = Appraisal.objects.get(pk=self.pk)
            if self.status == 'leave_application':
            # if original != self.status:
                logger.info(
                    f"[SECURITY] Status Change: Appraisal for {self.employee.id} "
                    f"moved from {self.status } to {self.status} by User ID: {self.tenant.code}"
                )
                
                # Special automation when reaching your custom state
                if self.status == 'leave_application':
                    self.calculate_score()
        if self.status == 'leave_application' and self.final_score >= 4.5:
                        logger.warning(
                            f"[TALENT ALERT] High Performer {self.employee.first_name}  {self.employee.first_name}  has reached "
                            f"Final Result stage for Tenant {self.tenant.code}. Immediate HR review recommended."
                        )
                            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Appraisal for {self.employee.first_name}  {self.employee.first_name} - Score: {self.final_score or 'N/A'}"
    

    class Meta:
        unique_together = ("employee", "cycle", "tenant")


class AppraisalCompetencyRating(TenantModel):
    """Ratings for specific competencies within an appraisal."""
    appraisal = models.ForeignKey(Appraisal, on_delete=models.CASCADE, related_name="competencies")
    competency = models.ForeignKey("development.Competency", on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comments = models.TextField(blank=True)

  
class AppraisalSkillRating(TenantModel):
    SOURCE_CHOICES = (
        ("SELF", "Self"),
        ("MANAGER", "Manager"),
    )

    appraisal = models.ForeignKey(
        Appraisal,
        on_delete=models.CASCADE,
        related_name="skill_ratings",
    )
    skill = models.ForeignKey(
        "development.Skill",
        on_delete=models.CASCADE,
        related_name="appraisal_ratings",
    )
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ("appraisal", "skill", "source")



class PerformanceService:
    def __init__(self, tenant):
        self.tenant = tenant

    def calculate_final_rating(self, appraisal_id):
        """
        World-class rating logic: 
        Final = (KPI_Score * 0.7) + (Competency_Score * 0.3)
        """
        appraisal = Appraisal.objects.get(id=appraisal_id, tenant=self.tenant)
        com_appraisal = AppraisalCompetencyRating.objects.get(id=appraisal_id, tenant=self.tenant)
        # 1. Average Competency Rating
        comp_ratings = com_appraisal.competency.all()
        avg_comp = comp_ratings.aggregate(models.Avg('rating'))['rating__avg'] or 0
        
        # 2. Logic for KPI Scores (Simplified)
        # In a real system, you'd compare actual vs target per weight
        kpi_score = appraisal.kpi_score # Assumes updated via separate logic
        
        # 3. Weighted Final Score
        final = (Decimal(kpi_score) * Decimal('0.7')) + (Decimal(avg_comp) * Decimal('0.3'))
        
        appraisal.competency_score = avg_comp
        appraisal.final_rating = final
        appraisal.save()
        
        return final

    def initiate_cycle(self, cycle_id):
        """Bulk creates blank appraisals for all active employees in a cycle."""
        cycle = AppraisalCycle.objects.get(id=cycle_id, tenant=self.tenant)
        employees = Employee.objects.filter(tenant=self.tenant, is_active=True)
        
        count = 0
        for emp in employees:
            obj, created = Appraisal.objects.get_or_create(
                tenant=self.tenant,
                employee=emp,
                cycle=cycle,
                defaults={'manager': emp.line_manager}
            )
            if created: count += 1
        return count
    
    
    
    def aggregate_360_to_appraisal(self, appraisal):
               
        """
    World-class logic: Calculates the average of all 360-responses 
    and updates the appraisal's competency score.
    """
      
        responses = FeedbackResponse.objects.filter(
            request__subject=appraisal.employee,
            request__cycle=appraisal.cycle,
            tenant=self.tenant
        )
        
        if responses.exists():
            avg_360 = responses.aggregate(models.Avg('average_rating'))['average_rating__avg']
            # Apply weighting: (Manager Score * 0.7) + (360 Average * 0.3)
            appraisal.competency_score = (appraisal.competency_score * Decimal('0.7')) + (Decimal(avg_360) * Decimal('0.3'))
            appraisal.save()
            
            logger.info(f"[TENANT: {self.tenant.code}] Integrated 360-feedback for {appraisal.employee}")
            
class AppraisalRating(TenantModel):
    """
    Stores individual scores for specific indicators within an appraisal.
    This allows for a side-by-side comparison of Self and Manager ratings.
    """
    appraisal = models.ForeignKey(
        Appraisal, 
        on_delete=models.CASCADE, 
        related_name="ratings",
        help_text="The parent appraisal record this rating belongs to."
    )
    indicator = models.ForeignKey(
        PerformanceIndicator, 
        on_delete=models.PROTECT,
        help_text="The KPI or Competency being measured."
    )
    
    # Self-Rating (Filled by Employee)
    self_score = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Score from 0 (Poor) to 5 (Excellent) as rated by the employee."
    )
    self_comment = models.TextField(
        blank=True,
        help_text="Employee's justification for their self-assigned score."
    )

    # Manager-Rating (Filled by Supervisor)
    manager_score = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Final score assigned by the manager after the review meeting."
    )
    manager_comment = models.TextField(
        blank=True,
        help_text="Manager's feedback regarding this specific indicator."
    )

    class Meta:
        unique_together = ('appraisal', 'indicator')
        verbose_name = "Appraisal Rating"
        verbose_name_plural = "Appraisal Ratings"

    def __str__(self):
        return f"{self.indicator.title}: {self.manager_score}/5"

    def save(self, *args, **kwargs):
        """
        Automated calculation trigger.
        Whenever a rating is saved, we update the parent appraisal's final score.
        """
        super().save(*args, **kwargs)
        # Recalculate parent score if the appraisal is in a state that allows it
        if self.appraisal.status in ['MANAGER_REVIEW', 'leave_application']:
            self.appraisal.calculate_score()



class TalentAnalyticsService:
    def __init__(self, tenant):
        self.tenant = tenant

    def get_employee_skill_gaps(self, employee):
        """
        Returns a list of gaps for a specific employee based on their current Grade.
        """
        # 1. Get the requirements for the employee's current grade
        requirements = GradeRequirement.objects.filter(
            tenant=self.tenant, 
            grade=employee.grade
        ).select_related('skill')

        gap_report = []

        for req in requirements:
            # 2. Get the actual skill level from the matrix
            actual_skill = SkillMatrix.objects.filter(
                tenant=self.tenant, 
                employee=employee, 
                skill=req.skill
            ).first()

            actual_level = actual_skill.level if actual_skill else 0
            gap = actual_level - req.minimum_level

            gap_report.append({
                "skill": req.skill.name,
                "required": req.minimum_level,
                "actual": actual_level,
                "gap": gap,
                "status": "Deficient" if gap < 0 else "Qualified" if gap == 0 else "Exceeds"
            })

        return gap_report

    def get_unit_training_needs(self, org_unit):
        """
        Aggregates gaps across an entire department to suggest training priorities.
        """
        from employees.models import Employee
        employees = Employee.objects.filter(job_roles__org_unit=org_unit, tenant=self.tenant)
        
        needs = {}
        for emp in employees:
            gaps = self.get_employee_skill_gaps(emp)
            for item in gaps:
                if item['gap'] < 0:
                    skill_name = item['skill']
                    needs[skill_name] = needs.get(skill_name, 0) + 1
        
        # Returns dict: {'Python': 15 employees need training, 'SQL': 4 employees}
        return dict(sorted(needs.items(), key=lambda item: item[1], reverse=True))
    
def get_talent_segmentation(self):
    """
    Segments employees based on Appraisal Score and Skill Gaps.
    """
    high_performers = Appraisal.objects.filter(
        tenant=self.tenant, 
        status='leave_application', # Your custom final state
        final_score__gte=4.5
    )
    
    # Logic to find "High Potential" (High Score + No Skill Gaps)
    hi_po = []
    for appraisal in high_performers:
        gaps = self.get_employee_skill_gaps(appraisal.employee)
        has_gaps = any(g['gap'] < 0 for g in gaps)
        if not has_gaps:
            hi_po.append(appraisal.employee)
            
    return hi_po


class NormalizationRule(TenantModel):
    cycle = models.OneToOneField(AppraisalCycle, on_delete=models.CASCADE)
    top_percent = models.PositiveIntegerField(default=10, help_text="Target % for High Performers")
    middle_percent = models.PositiveIntegerField(default=70, help_text="Target % for Core Performers")
    bottom_percent = models.PositiveIntegerField(default=20, help_text="Target % for Under Performers")

    def __str__(self):
        return f"Rule for {self.cycle.name}"
    

class NormalizationService:
    def __init__(self, tenant, cycle):
        self.tenant = tenant
        self.cycle = cycle

    def apply_bell_curve(self):
        """
        Ranks appraisals and assigns a 'Normalized Grade' based on percentile.
        """
        # 1. Get all completed/finalizing appraisals
        appraisals = Appraisal.objects.filter(
            tenant=self.tenant, 
            cycle=self.cycle,
            status__in=['REVIEW', 'leave_application']
        ).order_by('-final_score') # Rank highest to lowest

        total_count = appraisals.count()
        if total_count == 0:
            return

        # 2. Define Percentile Cut-offs
        # Top 10% get 'A', next 70% get 'B', bottom 20% get 'C'
        top_cutoff = int(total_count * 0.10)
        bottom_cutoff = int(total_count * 0.80)

        for index, appraisal in enumerate(appraisals):
            if index < top_cutoff:
                appraisal.normalized_grade = "A"
                appraisal.moderated_score = appraisal.final_score * Decimal('1.1') # Optional: slight boost
            elif index < bottom_cutoff:
                appraisal.normalized_grade = "B"
                appraisal.moderated_score = appraisal.final_score
            else:
                appraisal.normalized_grade = "C"
                appraisal.moderated_score = appraisal.final_score * Decimal('0.9') # Optional: slight penalty

            appraisal.save()

        return f"Normalized {total_count} appraisals."
    
class FeedbackRequest(TenantModel):
    """
    Manages the 'Who rates Whom' relationship.
    """
    RELATIONSHIP_CHOICES = [
        ("PEER", "Peer"),
        ("SUB", "Subordinate (Direct Report)"),
        ("MGR", "Manager (Upward Feedback)"),
        ("EXT", "External (Client/Vendor)"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
    ]
    
    cycle = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE)
    subject = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="received_360_requests")
    provider = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="provided_360_feedback")
    relationship = models.CharField(max_length=4, choices=RELATIONSHIP_CHOICES)
    
    is_anonymous = models.BooleanField(default=True, help_text="Hide provider identity from the subject?")
    is_completed = models.BooleanField(default=False)
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    class Meta:
        unique_together = ("cycle", "subject", "provider", "tenant")

class FeedbackResponse(TenantModel):
    """
    Captures the actual ratings and qualitative comments.
    """
    request = models.OneToOneField(FeedbackRequest, on_delete=models.CASCADE, related_name="response")
    
    # Quantitative: Average score across competencies
    average_rating = models.DecimalField(max_digits=3, decimal_places=2)
    
    # Qualitative: The "Stop, Start, Continue" framework
    what_to_start = models.TextField(help_text="What should this person start doing?")
    what_to_stop = models.TextField(help_text="What should this person stop doing?")
    what_to_continue = models.TextField(help_text="What are they doing well?")
    
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.request.subject} by {self.request.relationship}"
    
class SuccessionProfile(TenantModel):
    POTENTIAL_CHOICES = [
        (1, "Low Potential"),
        (2, "Moderate Potential"),
        (3, "High Potential"),
    ]
    
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="succession_profile")
    potential_score = models.PositiveIntegerField(choices=POTENTIAL_CHOICES, default=2)
    readiness_timeline = models.CharField(max_length=20, choices=[
        ('READY_NOW', 'Ready Now'),
        ('1_2_YEARS', '1-2 Years'),
        ('3_PLUS', '3+ Years'),
    ], default='1_2_YEARS')
    
    is_key_talent = models.BooleanField(default=False)
    risk_of_loss = models.CharField(max_length=10, choices=[('LOW', 'Low'), ('MED', 'Med'), ('HIGH', 'High')], default='LOW')
    impact_of_loss = models.CharField(max_length=10, choices=[('LOW', 'Low'), ('MED', 'Med'), ('HIGH', 'High')], default='LOW')

    def __str__(self):
        return f"Succession: {self.employee.full_name}"

    def get_9_box_coordinate(self):
        """
        Maps Performance (Final Score) and Potential to the 9-Box Grid.
        Performance: 1-5 scale mapped to Low(1-2), Med(3-4), High(5)
        """
        perf = self.employee.appraisals.filter(status='leave_application').first()
        perf_score = float(perf.final_score) if perf else 0
        
        # Mapping logic
        x = 1 if perf_score < 2.5 else 2 if perf_score < 4.0 else 3
        y = self.potential_score
        return x, y # Returns (Performance, Potential)