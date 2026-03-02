from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, TemplateView, CreateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from .models import LeaveRequest, LeaveBalance, LeaveType
import logging

import logging
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import TemplateView, CreateView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import LeaveRequestForm

logger = logging.getLogger(__name__)


def log_with_context(level, message, user):
    tenant = getattr(user, "tenant", None)
    logger.log(level, f"tenant={tenant}|user={user.username}|{message}")


class LeaveDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "leave/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee
        tenant = self.request.user.tenant
        year = timezone.now().year

        log_with_context(
            logging.INFO, "Accessing leave_application dashboard", self.request.user
        )

        # Balances
        context["balances"] = LeaveBalance.objects.filter(
            employee=employee, tenant=tenant, year=year
        )
        # Recent requests
        context["recent"] = LeaveRequest.objects.filter(
            employee=employee, tenant=tenant
        ).order_by("start_date")[:5]

        return context

import os
from django.contrib.auth.models import User
from employees.models import Employee
from org.models import JobRole, OrgUnit # Adjust imports to your app names
from django.db import transaction


class ApplyLeaveView(LoginRequiredMixin, CreateView):
    model = LeaveRequest
    template_name = "leave/apply_leave.html"
    fields = ["leave_type", "start_date", "end_date", "reason", "attachment"]
    success_url = reverse_lazy("leave:dashboard")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filter leave types for tenant
        queryset = LeaveType.objects.filter(
            tenant=self.request.user.tenant
        )
        
        # Filter Maternity Leave for female employees only
        gender = getattr(self.request.user.employee, 'gender', None)
        if gender != 'F':
            queryset = queryset.exclude(name__icontains='Maternity')
            
        form.fields["leave_type"].queryset = queryset
        return form

    def form_valid(self, form):
        try:
            form.instance.tenant = self.request.user.tenant
            form.instance.employee = self.request.user.employee
            leave_request = form.save()

            # Start Workflow
            from workflow.services.workflow_service import WorkflowService

            service = WorkflowService(self.request.user.tenant)
            service.trigger_workflow(
                workflow_code="leave-management",  # Assuming this code exists
                target=leave_request,
                started_by=self.request.user.employee,
            )

            log_with_context(
                logging.INFO,
                f"Leave submitted and workflow started for {leave_request}",
                self.request.user,
            )

            return super().form_valid(form)
        except Exception as e:
            logger.error(f"Error in ApplyLeaveView: {str(e)}", exc_info=True)
            form.add_error(None, "An error occurred while submitting your request.")
            return self.form_invalid(form)


class ApplyLeaveView1a(LoginRequiredMixin, CreateView):
    model = LeaveRequest
    form_class = LeaveRequestForm  # <-- use your custom form here

    template_name = "leave/apply_leave.html"
    # fields = ["leave_type", "start_date", "end_date", "reason", "attachment"]
    success_url = reverse_lazy("leave:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request  # pass request into the form
        log_with_context(
            logging.INFO,
            f"GEt  leave_application Form for {self.request.user.employee}",
            self.request.user,
        )
        return kwargs

    def form_valid(self, form):
        log_with_context(
            logging.INFO,
            f"New leave_application submitted for {form.instance.leave_type}",
            self.request.user,
        )
        return super().form_valid(form)


class LeaveHistoryView(LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = "leave/leave_history.html"
    context_object_name = "requests"

    def get_queryset(self):
        log_with_context(
            logging.INFO, "Viewing leave_application history", self.request.user
        )
        return LeaveRequest.objects.filter(
            employee=self.request.user.employee, tenant=self.request.user.tenant
        )


# --- Manager Views ---


class ManageLeaveView(LoginRequiredMixin, ListView):
    model = LeaveRequest
    template_name = "leave/manage_requests.html"
    context_object_name = "requests"

    def get_queryset(self):
        try:
            log_with_context(
                logging.INFO,
                "Manager accessing pending leave_applications",
                self.request.user,
            )
            return LeaveRequest.objects.filter(
                tenant=self.request.user.tenant,
                status="PENDING",
            ).exclude(employee=self.request.user.employee)
        except Exception as e:
            log_with_context(
                logging.ERROR, f"Error in ManageLeaveView: {str(e)}", self.request.user
            )
            return LeaveRequest.objects.none()


class ApproveLeaveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            leave_req = get_object_or_404(
                LeaveRequest, pk=pk, tenant=request.user.tenant
            )
            action = request.POST.get("action")  # 'approve' or 'reject'

            if action == "approve":
                leave_req.status = "APPROVED"
                leave_req.approved_by = request.user.employee
                leave_req.save()
                log_with_context(
                    logging.INFO,
                    f"leave_application approved for ID: {pk}",
                    request.user,
                )
                messages.success(request, "Leave Approved")

            elif action == "reject":
                leave_req.status = "REJECTED"
                leave_req.rejection_reason = request.POST.get("reason", "")
                leave_req.save()
                log_with_context(
                    logging.INFO,
                    f"leave_application rejected for ID: {pk}",
                    request.user,
                )
                messages.warning(request, "Leave Rejected")

        except Exception as e:
            log_with_context(
                logging.ERROR,
                f"Error in ApproveLeaveView (leave_application): {str(e)}",
                request.user,
            )
            messages.error(request, "An error occurred while processing the request.")

        return redirect("leave:manage_leaves")
