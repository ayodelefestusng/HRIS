
class OnboardingPlan(TenantModel):
    """
    The actual instance of onboarding for a specific hired candidate.
    """
    STATUS_CHOICES = [
        ("NOT_STARTED", "Not Started"),
        ("IN_PROGRESS", "In Progress"),
        ("leave_application", "Orientation Leave"), # Using your specific state requirement
        ("COMPLETED", "Completed"),
    ]

    # Link to ATS Application to pull candidate data automatically
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="onboarding_plan")
    mentor = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentoring_plans")
    start_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NOT_STARTED")
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0) # e.g., 75.00%

    def update_progress(self):
        total = self.tasks.count()
        if total > 0:
            completed = self.tasks.filter(is_completed=True).count()
            self.progress = (completed / total) * 100
            self.save(update_fields=['progress'])

    def __str__(self):
        return f"Onboarding: {self.application.candidate.full_name}"


