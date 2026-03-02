from django.urls import path, include
from .views import (
    ProcessPayrollView,
    ManagePayrollScheduleView,
    UpdatePayrollScheduleView,
    TaxComplianceView,
    GenerateTaxComplianceReportView,
    GeneratePayslipView,
    DownloadPayslipView,
    PayrollReportView,
    DownloadPayrollReportView,
    EmployeePayrollHistoryView,
    ViewEmployeePayrollHistoryView,
    PayrollDashboardView,
    # Keep existing if needed, but prioritizing new structure
    payroll_staging_area,
    activate_salary,
    RunPayrollView,
)

app_name = "payroll"

urlpatterns = [
    # Dashboard
    path("dashboard/", PayrollDashboardView.as_view(), name="dashboard"),
    # Payroll Processing
    path("process/", ProcessPayrollView.as_view(), name="process_payroll"),
    path(
        "process/<int:pk>/run/", RunPayrollView.as_view(), name="run_payroll"
    ),  # Kept as API/Action endpoint
    # Schedule Management
    path("schedule/", ManagePayrollScheduleView.as_view(), name="manage_schedule"),
    path(
        "schedule/<int:pk>/update/",
        UpdatePayrollScheduleView.as_view(),
        name="update_schedule",
    ),
    # Tax Compliance
    path("tax/compliance/", TaxComplianceView.as_view(), name="tax_compliance"),
    path(
        "tax/compliance/<int:pk>/generate/",
        GenerateTaxComplianceReportView.as_view(),
        name="generate_tax_report",
    ),
    # Payslips
    path("payslip/", GeneratePayslipView.as_view(), name="generate_payslip"),
    path(
        "payslip/<int:pk>/download/",
        DownloadPayslipView.as_view(),
        name="download_payslip",
    ),
    # Reporting
    path("report/", PayrollReportView.as_view(), name="payroll_report"),
    path(
        "report/<int:pk>/download/",
        DownloadPayrollReportView.as_view(),
        name="download_report",
    ),
    # History
    path("history/", EmployeePayrollHistoryView.as_view(), name="payroll_history"),
    path(
        "history/<int:pk>/",
        ViewEmployeePayrollHistoryView.as_view(),
        name="view_history",
    ),
    # Legacy / Utility
    path("staging/", payroll_staging_area, name="payroll_staging"),
    # path('activate/<int:employee_id>/', activate_salary, name='activate_salary'),
]
