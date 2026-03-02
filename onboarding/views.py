from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    View,
    CreateView,
    UpdateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.utils import timezone

# Importing models from other apps as Onboarding connects them
from ats.models import Application, OnboardingPlan, OnboardingTask
from employees.models import Employee, ExitProcess
import logging

logger = logging.getLogger(__name__)


class OnboardingDashboardView(LoginRequiredMixin, ListView):
    model = OnboardingPlan
    template_name = "onboarding/dashboard.html"
    context_object_name = "plans"

    def get_queryset(self):
        return OnboardingPlan.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("employee", "application")


class StartOnboardingView(LoginRequiredMixin, View):
    def get(self, request, application_id):
        try:
            # Logic to convert Application -> Onboarding Plan
            # This typically happens after "HIRED" status
            application = get_object_or_404(
                Application, application_id=application_id, tenant=request.user.tenant
            )

            # Check if plan exists
            if hasattr(application, "onboarding_plan"):
                return redirect(
                    "onboarding:task_list", pk=application.onboarding_plan.pk
                )

            # Create Plan Stub
            plan = OnboardingPlan.objects.create(
                tenant=request.user.tenant,
                application=application,
                start_date=timezone.now().date(),
                status="IN_PROGRESS",
            )
            return redirect("onboarding:task_list", pk=plan.pk)
        except Exception as e:
            logger.error(f"Error in StartOnboardingView: {str(e)}", exc_info=True)
            return redirect("onboarding:dashboard")


class OnboardingTaskListView(LoginRequiredMixin, DetailView):
    model = OnboardingPlan
    template_name = "onboarding/task_list.html"
    context_object_name = "plan"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Mocking tasks if none exist (Real logic would generate from Template)
        # context['tasks'] = self.object.tasks.all()
        return context


class CompleteTaskView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            task = get_object_or_404(OnboardingTask, pk=pk, tenant=request.user.tenant)
            task.is_completed = True
            task.completed_at = timezone.now()
            task.save()
            # Update plan progress
            task.plan.update_progress()
            return JsonResponse({"status": "completed", "progress": task.plan.progress})
        except Exception as e:
            logger.error(f"Error in CompleteTaskView: {str(e)}", exc_info=True)
            return JsonResponse(
                {"status": "error", "message": "Failed to complete task."}, status=500
            )


# --- Offboarding ---


class OffboardingDashboardView(LoginRequiredMixin, ListView):
    model = ExitProcess
    template_name = "onboarding/offboarding_dashboard.html"
    context_object_name = "exits"

    def get_queryset(self):
        return ExitProcess.objects.filter(
            tenant=self.request.user.tenant
        ).select_related("employee")


class InitiateOffboardingView(LoginRequiredMixin, CreateView):
    model = ExitProcess
    template_name = "onboarding/initiate_offboarding.html"
    fields = ["exit_type", "notice_date", "exit_date", "reason"]
    success_url = reverse_lazy("onboarding:offboarding_dashboard")

    def form_valid(self, form):
        form.instance.tenant = self.request.user.tenant
        employee = get_object_or_404(
            Employee, pk=self.kwargs["employee_id"], tenant=self.request.user.tenant
        )
        form.instance.employee = employee
        return super().form_valid(form)


class ExitInterviewView(LoginRequiredMixin, UpdateView):
    model = ExitProcess
    template_name = "onboarding/exit_interview.html"
    fields = ["interview_notes"]  # Simplified
    success_url = reverse_lazy("onboarding:offboarding_dashboard")
