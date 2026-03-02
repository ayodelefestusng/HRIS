class OnboardingPlan(TenantModel):
    """
    The orchestrator. Links a Candidate from ATS to their new Employee profile.
    """
    STATUS_CHOICES = [
        ("NOT_STARTED", "Not Started"),
        ("IN_PROGRESS", "In Progress"),
        ("leave_application", "Orientation Phase"), # Your custom state
        ("COMPLETED", "Completed"),
    ]

    application = models.OneToOneField('ats.Application', on_delete=models.CASCADE, related_name="onboarding_plan")
    # Once they start, they get an Employee profile
    employee = models.OneToOneField('employees.Employee', on_delete=models.SET_NULL, null=True, related_name="onboarding_plan")
    mentor = models.ForeignKey('employees.Employee', on_delete=models.SET_NULL, null=True, blank=True)
    
    start_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NOT_STARTED")
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # The Workflow instance that tracks the OVERALL onboarding process
    workflow_instance = models.ForeignKey('WorkflowInstance', on_delete=models.SET_NULL, null=True)

    def update_progress(self):
        total = self.tasks.count()
        if total > 0:
            completed = self.tasks.filter(is_completed=True).count()
            self.progress = (completed / total) * 100
            self.save(update_fields=['progress'])
            
            if self.progress == 100 and self.status != "COMPLETED":
                # Trigger logic to change employee status to ACTIVE
                pass