from django.urls import path
from .views import (
    LeaveDashboardView,
    ApplyLeaveView,
    LeaveHistoryView,
    ManageLeaveView,
    ApproveLeaveView,
)

app_name = "leave"

urlpatterns = [
    # Employee Self Service
    path("dashboard/", LeaveDashboardView.as_view(), name="dashboard"),
    path("apply/", ApplyLeaveView.as_view(), name="apply_leave"),
    path("history/", LeaveHistoryView.as_view(), name="my_history"),
    # Manager Action
    path("manage/", ManageLeaveView.as_view(), name="manage_leaves"),
    path("approve/<int:pk>/", ApproveLeaveView.as_view(), name="approve_leave"),
]
