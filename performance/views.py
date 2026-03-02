from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    View,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Avg

from .models import (
    Appraisal,
    PerformanceIndicator,
    AppraisalRating,
    FeedbackRequest,
    FeedbackResponse,
    AppraisalCycle,
)
from employees.models import Employee

# --- Dashboard ---


class AppraisalDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "performance/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_emp = self.request.user.employee  # Assumes employee linked

        # My Appraisals
        context["my_appraisals"] = Appraisal.objects.filter(employee=user_emp)

        # Pending Reviews (As Manager)
        context["pending_reviews"] = Appraisal.objects.filter(
            manager=user_emp, approval_status="review"
        )

        # 360 Feedback Requests
        context["feedback_requests"] = FeedbackRequest.objects.filter(
            provider=user_emp, status="PENDING"
        )

        context["active_cycle"] = AppraisalCycle.objects.filter(
            tenant=self.request.user.tenant, status="ACTIVE"
        ).first()
        return context


# --- Appraisal Process ---


class StartAppraisalView(LoginRequiredMixin, View):
    def post(self, request, employee_id):
        # Stub to initiate appraisal logic
        # Check active cycle
        cycle = AppraisalCycle.objects.filter(
            tenant=request.user.tenant, status="ACTIVE"
        ).first()
        if not cycle:
            return JsonResponse({"error": "No active appraisal cycle"}, status=400)

        employee = get_object_or_404(
            Employee, pk=employee_id, tenant=request.user.tenant
        )
        manager = employee.reports_to

        appraisal = Appraisal.objects.create(
            tenant=request.user.tenant,
            cycle=cycle,
            employee=employee,
            manager=manager,
            status="SELF_REVIEW",
            start_date=timezone.now().date(),
        )
        return redirect("performance:self_appraisal", pk=appraisal.pk)


class SelfAppraisalView(LoginRequiredMixin, UpdateView):
    model = Appraisal
    template_name = "performance/self_appraisal.html"
    fields = ["employee_comments"]  # Simplified for stub

    def form_valid(self, form):
        if "submit" in self.request.POST:
            form.instance.status = "MANAGER_REVIEW"
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("performance:dashboard")


class ManagerAppraisalView(LoginRequiredMixin, UpdateView):
    model = Appraisal
    template_name = "performance/manager_appraisal.html"
    fields = ["manager_comments", "manager_rating"]  # Simplified

    def form_valid(self, form):
        if "submit" in self.request.POST:
            form.instance.status = "COMPLETED"  # Or Review, etc.
            # Calculate final score logic here
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("performance:dashboard")


class ReviewAppraisalView(LoginRequiredMixin, DetailView):
    model = Appraisal
    template_name = "performance/review_appraisal.html"


# --- KPIs ---


class KPIListView(LoginRequiredMixin, ListView):
    model = PerformanceIndicator
    template_name = "performance/kpi_list.html"
    context_object_name = "kpis"

    def get_queryset(self):
        return PerformanceIndicator.objects.filter(tenant=self.request.user.tenant)


class CreateKPIView(LoginRequiredMixin, CreateView):
    model = PerformanceIndicator
    template_name = "performance/create_kpi.html"
    fields = ["name", "description", "target_value", "weight"]
    success_url = reverse_lazy("performance:kpi_list")

    def form_valid(self, form):
        form.instance.tenant = self.request.user.tenant
        return super().form_valid(form)


# --- 360 Feedback ---


class FeedbackRequestView(LoginRequiredMixin, CreateView):
    model = FeedbackRequest
    template_name = "performance/request_feedback.html"
    fields = ["reviewer", "message", "due_date"]
    success_url = reverse_lazy("performance:dashboard")

    def form_valid(self, form):
        form.instance.tenant = self.request.user.tenant
        form.instance.requester = self.request.user.employee
        return super().form_valid(form)


class ProvideFeedbackView(LoginRequiredMixin, UpdateView):
    model = FeedbackRequest
    template_name = "performance/provide_feedback.html"
    fields = ["feedback_text"]  # Simplified

    def form_valid(self, form):
        form.instance.status = "COMPLETED"
        form.instance.completed_at = timezone.now()
        # Create FeedbackResponse logic
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("performance:dashboard")


# --- Normalization ---


class NormalizationView(LoginRequiredMixin, TemplateView):
    template_name = "performance/normalization.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Stub for Bell curve data
        context["avg_rating"] = Appraisal.objects.filter(
            tenant=self.request.user.tenant
        ).aggregate(Avg("final_score"))
        return context
