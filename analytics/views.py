from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from .models import MetricSnapshot
from employees.models import Employee, ExitProcess
from ats.models import Application
from performance.models import Appraisal
from payroll.models import Payslip
import logging

logger = logging.getLogger(__name__)
import logging
from django.utils import timezone
from django.db.models import Count, Sum
from django.shortcuts import redirect
from django.views.generic import TemplateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin

logger = logging.getLogger(__name__)

def log_with_context(level, message, user):
    tenant = getattr(user, "tenant", None)
    logger.log(
        level,
        f"tenant={tenant}|user={user.username}|{message}"
    )

class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/dashboard.html"

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            tenant = self.request.user.tenant
            log_with_context(logging.INFO, "Accessing AnalyticsDashboardView", self.request.user)

            # Real-time Metrics
            context["total_employees"] = Employee.objects.filter(
                tenant=tenant, is_active=True
            ).count()
            context["departments"] = (
                Employee.objects.filter(tenant=tenant, is_active=True)
                .values("department__name")
                .annotate(count=Count("id"))
            )

            # Recent Snapshots
            context["recent_snapshots"] = MetricSnapshot.objects.filter(
                tenant=tenant
            ).order_by("-captured_at")[:5]

            log_with_context(logging.INFO, "AnalyticsDashboardView context prepared", self.request.user)
            return context
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in AnalyticsDashboardView: {str(e)}", self.request.user)
            return {}


class TurnoverAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/turnover.html"

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            tenant = self.request.user.tenant
            log_with_context(logging.INFO, "Accessing TurnoverAnalyticsView", self.request.user)

            exits_count = ExitProcess.objects.filter(
                tenant=tenant, exit_date__year=timezone.now().year
            ).count()
            active_count = Employee.objects.filter(tenant=tenant, is_active=True).count()

            turnover_rate = 0
            if active_count > 0:
                turnover_rate = (exits_count / active_count) * 100

            context["exits_this_year"] = exits_count
            context["turnover_rate"] = round(turnover_rate, 2)
            context["exit_reasons"] = (
                ExitProcess.objects.filter(tenant=tenant)
                .values("reason")
                .annotate(count=Count("id"))
            )

            log_with_context(logging.INFO, f"TurnoverAnalytics calculated exits={exits_count}, rate={turnover_rate}%", self.request.user)
            return context
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in TurnoverAnalyticsView: {str(e)}", self.request.user)
            return {}

class RecruitmentAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "analytics/recruitment.html"

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            tenant = self.request.user.tenant
            log_with_context(logging.INFO, "Accessing RecruitmentAnalyticsView", self.request.user)

            context["total_applications"] = Application.objects.filter(
                tenant=tenant
            ).count()
            context["hired_count"] = Application.objects.filter(
                tenant=tenant, status="HIRED"
            ).count()

            # Pipeline Funnel
            context["funnel"] = (
                Application.objects.filter(tenant=tenant)
                .values("status")
                .annotate(count=Count("id"))
            )
            
            log_with_context(logging.INFO, "RecruitmentAnalytics context prepared", self.request.user)
            return context
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in RecruitmentAnalyticsView: {str(e)}", self.request.user)
            return {}


class GenerateSnapshotView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            log_with_context(logging.INFO, "Starting manual snapshot generation", request.user)
            tenant = request.user.tenant

            # Example: Capture Headcount
            metrics = {
                "total_emp": Employee.objects.filter(
                    tenant=tenant, is_active=True
                ).count(),
                "total_salary_cost": Payslip.objects.filter(tenant=tenant).aggregate(
                    Sum("net_pay")
                )["net_pay__sum"] or 0,
            }

            MetricSnapshot.objects.create(
                tenant=tenant, report_type="HEADCOUNT", metrics=metrics
            )
            
            log_with_context(logging.INFO, "Snapshot generated successfully", request.user)
            return redirect("analytics:dashboard")
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in GenerateSnapshotView: {str(e)}", request.user)
            return redirect("analytics:dashboard")


class ReportDetailView(LoginRequiredMixin, DetailView):
    model = MetricSnapshot
    template_name = "analytics/report_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        log_with_context(logging.INFO, f"Viewing ReportDetail ID: {self.object.pk}", self.request.user)
        return context


class ExportReportView(LoginRequiredMixin, View):
    def get(self, request, pk):
        log_with_context(logging.INFO, f"Initiating report export for ID: {pk}", request.user)
        # Stub for CSV/PDF export
        return redirect("analytics:report_detail", pk=pk)