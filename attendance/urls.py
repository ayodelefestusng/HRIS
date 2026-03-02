from django.urls import path
from .views import (
    TrackAttendanceView,
    LateArrivalsView,
    EarlyDeparturesView,
    BiometricIntegrationView,
    AttendanceReportView,
    AbsenteeismReportView,
    TardinessReportView,
    # Additional features
    LeaveManagementView,
    AttendanceAnalyticsView,
    SmartClockView
)

app_name = "attendance"

urlpatterns = [
    # Tracking
    path("track/", TrackAttendanceView.as_view(), name="track_attendance"),
    path("track/late/", LateArrivalsView.as_view(), name="late_arrivals"),
    path("track/early/", EarlyDeparturesView.as_view(), name="early_departures"),
    # Biometric Stub
    path(
        "biometric/integrate/",
        BiometricIntegrationView.as_view(),
        name="biometric_integration",
    ),
    # Reporting
    path("report/", AttendanceReportView.as_view(), name="attendance_report"),
    path(
        "report/absenteeism/",
        AbsenteeismReportView.as_view(),
        name="absenteeism_report",
    ),
    path("smart-clock/", SmartClockView.as_view(), name="smart_clock"), 
    path("report/tardiness/", TardinessReportView.as_view(), name="tardiness_report"),
    # Analytics / Management
    path("analytics/", AttendanceAnalyticsView.as_view(), name="attendance_analytics"),
    path("leaves/", LeaveManagementView.as_view(), name="manage_leaves"),
]
