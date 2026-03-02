from django.urls import path
from .views import (
    AppraisalDashboardView,
    StartAppraisalView,
    SelfAppraisalView,
    ManagerAppraisalView,
    ReviewAppraisalView,
    KPIListView,
    CreateKPIView,
    FeedbackRequestView,
    ProvideFeedbackView,
    NormalizationView,
)

app_name = "performance"

urlpatterns = [
    # Dashboard
    path("dashboard/", AppraisalDashboardView.as_view(), name="dashboard"),
    # Appraisal Process
    path(
        "appraisal/start/<int:employee_id>/",
        StartAppraisalView.as_view(),
        name="start_appraisal",
    ),
    path(
        "appraisal/<int:pk>/self/", SelfAppraisalView.as_view(), name="self_appraisal"
    ),
    path(
        "appraisal/<int:pk>/manager/",
        ManagerAppraisalView.as_view(),
        name="manager_appraisal",
    ),
    path(
        "appraisal/<int:pk>/review/",
        ReviewAppraisalView.as_view(),
        name="review_appraisal",
    ),
    # KPI Management
    path("kpis/", KPIListView.as_view(), name="kpi_list"),
    path("kpis/create/", CreateKPIView.as_view(), name="create_kpi"),
    # 360 Feedback
    path("feedback/request/", FeedbackRequestView.as_view(), name="request_feedback"),
    path(
        "feedback/provide/<int:pk>/",
        ProvideFeedbackView.as_view(),
        name="provide_feedback",
    ),
    # Admin / Normalization
    path("normalization/", NormalizationView.as_view(), name="normalization"),
]
