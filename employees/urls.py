from django.urls import path
from .views import (
    EmployeeListView,
    EmployeeDetailView,
    EmployeeUpdateView,
    DocumentListView,
    UploadDocumentView,
    PolicyListView,
    AcknowledgePolicyView,
    BenefitsListView,
    EnrollBenefitView,
    ProfileUpdateRequestView,
)

app_name = "employees"

urlpatterns = [
    # Profile Management
    path("list/", EmployeeListView.as_view(), name="employee_list"),
    path("detail/<int:pk>/", EmployeeDetailView.as_view(), name="employee_detail"),
    path("update/<int:pk>/", EmployeeUpdateView.as_view(), name="employee_update"),
    path("request-update/", ProfileUpdateRequestView.as_view(), name="request_update"),

    # Document Management
    path("documents/<int:pk>/", DocumentListView.as_view(), name="document_list"),
    path(
        "documents/<int:pk>/upload/",
        UploadDocumentView.as_view(),
        name="upload_document",
    ),
    # Compliance & Policy
    path("policies/", PolicyListView.as_view(), name="policy_list"),
    path(
        "policies/acknowledge/<int:pk>/",
        AcknowledgePolicyView.as_view(),
        name="acknowledge_policy",
    ),
    # Benefits
    path("benefits/", BenefitsListView.as_view(), name="benefit_list"),
    path(
        "benefits/enroll/<int:pk>/", EnrollBenefitView.as_view(), name="enroll_benefit"
    ),
]
