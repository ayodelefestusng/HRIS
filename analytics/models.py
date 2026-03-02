from django.db import models
from django.utils import timezone
from org.models import TenantModel


class MetricSnapshot(TenantModel):
    """
    Stores periodic analytics snapshots (daily, weekly, monthly) for trend analysis.
    """

    REPORT_TYPES = [
        ("HEADCOUNT", "Headcount & Demographics"),
        ("TURNOVER", "Attrition & Turnover"),
        ("PAYROLL", "Payroll Costs"),
        ("ATTENDANCE", "Attendance Stats"),
        ("PERFORMANCE", "Performance Distribution"),
    ]

    report_type = models.CharField(
        max_length=20, choices=REPORT_TYPES, default="HEADCOUNT"
    )
    captured_at = models.DateTimeField(default=timezone.now)
    metrics = models.JSONField(default=dict)

    # Store reference to range if needed
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-captured_at"]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.captured_at.date()}"
