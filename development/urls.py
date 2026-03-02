from django.urls import path
from .views import (
    CourseListView,
    TrainingSessionDetailView,
    EnrollView,
    MyLearningView,
    SkillMatrixView,
    SkillGapAnalysisView,
)

app_name = "development"

urlpatterns = [
    # Learning
    path("courses/", CourseListView.as_view(), name="course_list"),
    path(
        "training/<int:pk>/",
        TrainingSessionDetailView.as_view(),
        name="training_session",
    ),
    path("enroll/<int:pk>/", EnrollView.as_view(), name="enroll_session"),
    path("my-learning/", MyLearningView.as_view(), name="my_learning"),
    # Skills
    path("skills/matrix/", SkillMatrixView.as_view(), name="skill_matrix"),
    path("skills/gap/", SkillGapAnalysisView.as_view(), name="gap_analysis"),
]
