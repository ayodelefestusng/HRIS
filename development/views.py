from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone

from .models import (
    Course,
    TrainingSession,
    Enrollment,
    SkillMatrix,
    Skill,
    GradeRequirement,
)
import logging

logger = logging.getLogger(__name__)

import logging
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin

logger = logging.getLogger(__name__)

def log_with_context(level, message, user):
    tenant = getattr(user, "tenant", None)
    logger.log(
        level,
        f"tenant={tenant}|user={user.username}|{message}"
    )

class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = "development/course_list.html"
    context_object_name = "courses"

    def get_queryset(self):
        try:
            log_with_context(logging.INFO, "Accessing available courses list", self.request.user)
            return Course.objects.filter(
                tenant=self.request.user.tenant
            ).prefetch_related("sessions")
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in CourseListView: {str(e)}", self.request.user)
            return Course.objects.none()


class TrainingSessionDetailView(LoginRequiredMixin, DetailView):
    model = TrainingSession
    template_name = "development/training_session.html"
    context_object_name = "session"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        log_with_context(logging.INFO, f"Viewing training session detail: ID {self.object.pk}", self.request.user)
        
        # Check if user is already enrolled
        context["is_enrolled"] = Enrollment.objects.filter(
            session=self.object, employee=self.request.user.employee
        ).exists()
        return context


class EnrollView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            session = get_object_or_404(
                TrainingSession, pk=pk, tenant=request.user.tenant
            )
            employee = request.user.employee

            # Check capacity
            current_count = session.enrollments.count()
            if current_count >= session.capacity:
                log_with_context(logging.WARNING, f"Enrollment failed: Session {pk} is at capacity ({session.capacity})", request.user)
                return JsonResponse({"error": "Session is full"}, status=400)

            obj, created = Enrollment.objects.get_or_create(
                tenant=request.user.tenant,
                employee=employee,
                session=session,
                defaults={"status": "ENR"},
            )
            
            status_msg = "New enrollment created" if created else "User already enrolled"
            log_with_context(logging.INFO, f"{status_msg} for Session ID: {pk}", request.user)
            
            return redirect("development:my_learning")
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in EnrollView: {str(e)}", request.user)
            return JsonResponse({"error": "Enrollment failed"}, status=500)


class MyLearningView(LoginRequiredMixin, ListView):
    template_name = "development/my_learning.html"
    context_object_name = "enrollments"

    def get_queryset(self):
        log_with_context(logging.INFO, "Accessing 'My Learning' personal dashboard", self.request.user)
        return Enrollment.objects.filter(
            employee=self.request.user.employee, tenant=self.request.user.tenant
        ).order_by("-enrolled_at")


class SkillMatrixView(LoginRequiredMixin, TemplateView):
    template_name = "development/skill_matrix.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee
        log_with_context(logging.INFO, "Viewing personal skill matrix and gap analysis", self.request.user)
        
        # Show gap analysis: Required vs Actual
        if employee.job_role and employee.job_role.grade:
            required = GradeRequirement.objects.filter(grade=employee.job_role.grade)

            matrix = []
            for req in required:
                actual = SkillMatrix.objects.filter(
                    employee=employee, skill=req.skill
                ).first()
                actual_level = actual.level if actual else 0
                matrix.append(
                    {
                        "skill": req.skill.name,
                        "required": req.minimum_level,
                        "actual": actual_level,
                        "gap": actual_level - req.minimum_level,
                    }
                )
            context["gap_matrix"] = matrix

        return context


class SkillGapAnalysisView(LoginRequiredMixin, TemplateView):
    template_name = "development/gap_analysis.html"
    
    def get_context_data(self, **kwargs):
        log_with_context(logging.INFO, "Manager accessing team Skill Gap Analysis", self.request.user)
        return super().get_context_data(**kwargs)