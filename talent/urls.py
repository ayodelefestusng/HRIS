from django.urls import path, include
from rest_framework.routers import DefaultRouter
from talent.views import (
    RoleProfileViewSet,
    CompetencyViewSet,
    SkillViewSet,
    RoleCompetencyRequirementViewSet,
    EmployeeSkillProfileViewSet,
    EmployeeRoleFitView,
)

router = DefaultRouter()
router.register("roles", RoleProfileViewSet, basename="role-profile")
router.register("competencies", CompetencyViewSet, basename="competency")
router.register("skills", SkillViewSet, basename="skill")
router.register(
    "role-competencies",
    RoleCompetencyRequirementViewSet,
    basename="role-competency-requirement",
)
router.register(
    "employee-skills",
    EmployeeSkillProfileViewSet,
    basename="employee-skill-profile",
)

urlpatterns = [
    path("", include(router.urls)),
    path("role-fit/<int:role_id>/", EmployeeRoleFitView.as_view()),
]

from talent.views import AppraisalViewSet, SubmitSelfRatingsView, ManagerReviewAppraisalView

router.register("appraisals", AppraisalViewSet, basename="appraisal")

urlpatterns += [
    path("appraisals/<int:appraisal_id>/self-submit/", SubmitSelfRatingsView.as_view()),
    path("appraisals/<int:appraisal_id>/manager-review/", ManagerReviewAppraisalView.as_view()),

path("role-fit/employee/<int:role_id>/", EmployeeRoleFitView.as_view()),
path("role-fit/candidate/<int:candidate_id>/<int:role_id>/", CandidateRoleFitView.as_view()),
path("orgchart/data/", OrgChartDataView.as_view()),

]

