from django.urls import path

from .views import (
    OrgDashboardView,
    DepartmentListView,
    DepartmentDetailView,
    JobRoleListView,
    OrgChartView,
    LocationListView,
    CreateUnitView,
    UpdateUnitView,
)

app_name = "org"

urlpatterns = [
    # Dashboard
    path("dashboard/", OrgDashboardView.as_view(), name="dashboard"),
    # Structure
    path("chart/", OrgChartView.as_view(), name="org_chart"),
    path("departments/", DepartmentListView.as_view(), name="department_list"),
    path(
        "departments/<int:pk>/",
        DepartmentDetailView.as_view(),
        name="department_detail",
    ),
    path("locations/", LocationListView.as_view(), name="location_list"),
    # Job Roles
    path("roles/", JobRoleListView.as_view(), name="job_role_list"),
    # Management
    path("unit/create/", CreateUnitView.as_view(), name="create_unit"),
    path("unit/<int:pk>/update/", UpdateUnitView.as_view(), name="update_unit"),
]
