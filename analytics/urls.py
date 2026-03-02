from django.urls import path
from .views import (
    AnalyticsDashboardView,
    GenerateSnapshotView,
    ReportDetailView,
    ExportReportView,
    TurnoverAnalyticsView,
    RecruitmentAnalyticsView,
)

app_name = "analytics"

urlpatterns = [
    path("dashboard/", AnalyticsDashboardView.as_view(), name="dashboard"),
    path(
        "generate-snapshot/", GenerateSnapshotView.as_view(), name="generate_snapshot"
    ),
    # Specific Domain Analytics
    path("turnover/", TurnoverAnalyticsView.as_view(), name="turnover_analytics"),
    path(
        "recruitment/", RecruitmentAnalyticsView.as_view(), name="recruitment_analytics"
    ),
    # Detail & Export
    path("report/<int:pk>/", ReportDetailView.as_view(), name="report_detail"),
    path("report/<int:pk>/export/", ExportReportView.as_view(), name="export_report"),
]
