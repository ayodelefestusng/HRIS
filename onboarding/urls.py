from django.urls import path
from .views import (
    OnboardingDashboardView,
    StartOnboardingView,
    OnboardingTaskListView,
    CompleteTaskView,
    OffboardingDashboardView,
    InitiateOffboardingView,
    ExitInterviewView,
)

app_name = "onboarding"

urlpatterns = [
    # Onboarding
    path("dashboard/", OnboardingDashboardView.as_view(), name="dashboard"),
    path(
        "start/<uuid:application_id>/",
        StartOnboardingView.as_view(),
        name="start_onboarding",
    ),
    path("tasks/<int:pk>/", OnboardingTaskListView.as_view(), name="task_list"),
    path("task/<int:pk>/complete/", CompleteTaskView.as_view(), name="complete_task"),
    # Offboarding
    path(
        "offboarding/dashboard/",
        OffboardingDashboardView.as_view(),
        name="offboarding_dashboard",
    ),
    path(
        "offboarding/initiate/<int:employee_id>/",
        InitiateOffboardingView.as_view(),
        name="initiate_offboarding",
    ),
    path(
        "offboarding/exit-interview/<int:pk>/",
        ExitInterviewView.as_view(),
        name="exit_interview",
    ),
]
