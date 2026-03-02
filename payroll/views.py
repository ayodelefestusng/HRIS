from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    View,
)
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Sum, Count, F
from xhtml2pdf import pisa
import logging

from .models import PayrollPeriod, PayrollEntry, Payslip, TaxRecord, EmployeePayslip
from employees.models import Employee
from .tasks import run_payroll  # Assuming this exists from previous code

logger = logging.getLogger(__name__)


def log_with_context(level, message, user):
    tenant = getattr(user, "tenant", None)
    logger.log(
        level,
        f"tenant={tenant}|user={user.username}|{message}"
    )
# --- Dashboard ---
class PayrollDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "payroll/dashboard.html"

    def get_context_data(self, **kwargs):
        try:
            log_with_context(logging.INFO, "Accessing Payroll Dashboard", self.request.user)
            context = super().get_context_data(**kwargs)
            tenant = getattr(self.request.user, "tenant", None)
        
            context["recent_periods"] = PayrollPeriod.objects.filter(tenant=tenant).order_by("-start_date")[:5]
            context["active_payroll"] = PayrollPeriod.objects.filter(tenant=tenant, status="OPN").first()
            context["total_payroll_cost"] = (PayrollEntry.objects.filter(
                tenant=tenant, 
                period__start_date__year=timezone.now().year
            ).aggregate(total=Sum("gross_salary"))["total"] or 0)

            return context
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in PayrollDashboardView: {str(e)}", self.request.user)
            return {"error": "Dashboard failed to load."}
# --- Processing ---


class ProcessPayrollView(LoginRequiredMixin, ListView):
    model = PayrollPeriod
    template_name = "payroll/process_payroll.html"
    context_object_name = "periods"

    def get_queryset(self):
        # Return open or pending periods usually
        return PayrollPeriod.objects.filter(tenant=self.request.user.tenant).order_by(
            "-start_date"
        )


class RunPayrollView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            log_with_context(logging.WARNING, f"Triggering background payroll run for Period ID: {pk}", request.user)
            # Trigger the background task (e.g., Celery)
            run_payroll.delay(pk)
            return JsonResponse({
                "status": "processing",
                "message": "Payroll calculation started in background.",
            })
        except Exception as e:
            log_with_context(logging.ERROR, f"Failed to start payroll task for Period {pk}: {str(e)}", request.user)
            return JsonResponse({"status": "error", "message": "Failed to start payroll."}, status=500)
# --- Schedule Management ---


class ManagePayrollScheduleView(LoginRequiredMixin, ListView):
    model = PayrollPeriod
    template_name = "payroll/manage_schedule.html"
    context_object_name = "schedules"

    def get_queryset(self):
        return PayrollPeriod.objects.filter(tenant=self.request.user.tenant).order_by(
            "-start_date"
        )


class UpdatePayrollScheduleView(LoginRequiredMixin, UpdateView):
    model = PayrollPeriod
    template_name = "payroll/update_schedule.html"
    fields = ["name", "start_date", "end_date", "status"]
    success_url = reverse_lazy("payroll:manage_schedule")

    def get_queryset(self):
        return PayrollPeriod.objects.filter(tenant=self.request.user.tenant)


# --- Tax Compliance ---


class TaxComplianceView(LoginRequiredMixin, ListView):
    model = TaxRecord
    template_name = "payroll/tax_compliance.html"
    context_object_name = "tax_records"

    def get_queryset(self):
        # Maybe filter by latest closed period by default
        return TaxRecord.objects.filter(tenant=self.request.user.tenant).select_related(
            "employee", "period"
        )


class GenerateTaxComplianceReportView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            period = get_object_or_404(PayrollPeriod, pk=pk, tenant=request.user.tenant)
            log_with_context(logging.INFO, f"Generating Tax Compliance Report for {period.name}", request.user)
            
            # Logic placeholder
            return HttpResponse(f"Generated Tax Report for {period.name}", content_type="text/plain")
        except Exception as e:
            log_with_context(logging.ERROR, f"Tax Report generation error: {str(e)}", request.user)
            return HttpResponse("Error generating report.", status=500)
# --- Payslips ---


class GeneratePayslipView(LoginRequiredMixin, ListView):
    model = EmployeePayslip  # or Payslip, depending on which one is the finalized one
    template_name = "payroll/generate_payslip.html"
    context_object_name = "payslips_ready"

    def get_queryset(self):
        # Show payslips from the most recent closed period?
        return Payslip.objects.filter(tenant=self.request.user.tenant).order_by(
            "-generated_at"
        )


# --- Payslips ---

class DownloadPayslipView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            payslip = get_object_or_404(Payslip, pk=pk, tenant=request.user.tenant)
            log_with_context(logging.INFO, f"User downloading payslip ID: {pk} (Employee: {payslip.employee.employee_id})", request.user)

            context = {
                "payslip": payslip,
                "employee": payslip.employee,
                "period": payslip.period,
            }

            html = render_to_string("payroll/payslip_pdf_template.html", context)
            response = HttpResponse(content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="payslip_{payslip.employee.employee_id}.pdf"'

            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                log_with_context(logging.ERROR, f"PDF Engine error for payslip {pk}", request.user)
                return HttpResponse("PDF generation error", status=500)
            
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"DownloadPayslipView Error: {str(e)}", request.user)
            return HttpResponse("Error generating payslip PDF.", status=500)
# --- Reporting ---


class PayrollReportView(LoginRequiredMixin, TemplateView):
    template_name = "payroll/report_dashboard.html"


class DownloadPayrollReportView(LoginRequiredMixin, View):
    def get(self, request, pk):
        # pk could be report type or period id
        return HttpResponse("Download Payroll Report logic here")


# --- History ---

class EmployeePayrollHistoryView(LoginRequiredMixin, ListView):
    model = PayrollEntry
    template_name = "payroll/employee_history_list.html"
    context_object_name = "entries"

    def get_queryset(self):
        log_with_context(logging.INFO, "Accessing historical payroll entries", self.request.user)
        return PayrollEntry.objects.filter(tenant=self.request.user.tenant)

# --- Legacy / Utility Helpers ---

class ViewEmployeePayrollHistoryView(LoginRequiredMixin, DetailView):
    model = PayrollEntry
    template_name = "payroll/employee_history_detail.html"
    context_object_name = "entry"

    def get_queryset(self):
        return PayrollEntry.objects.filter(tenant=self.request.user.tenant)


# --- Legacy / Utility Helpers kept from previous file ---


# --- Legacy / Utility Helpers ---

def payroll_staging_area(request):
    log_with_context(logging.INFO, "Viewing payroll staging area for new hires", request.user)
    new_hires = Employee.objects.filter(
        tenant=request.user.tenant,
        status="ACTIVE",
        payroll_entries__isnull=True,
    )
    return render(request, "payroll/staging.html", {"new_hires": new_hires})
def activate_salary(request, employee_id):
    # Stub
    return HttpResponse(f'<span class="badge bg-success">Activated</span>')
