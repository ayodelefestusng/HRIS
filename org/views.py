from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Count

from .models import (
    OrgUnit,
    Department,
    JobRole,
    Location,
    Unit,  # Assuming Unit is a model for generic org units if OrgUnit is base
)
import logging
from django.db.models import Count
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

import logging
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
logger = logging.getLogger(__name__)
from django.views import View
from django.views.generic import View, TemplateView, DetailView

logger = logging.getLogger(__name__)

def log_with_contextV4(level, message, user):
    tenant = getattr(user, "tenant", None)
    logger.log(level,f"tenant={tenant}|user={user.username}|{message}")
def log_with_context(level, message, user):
    tenant = getattr(user, "tenant", "Global")
    username = getattr(user, "username", None) or str(user)
    logger.log(level, f"tenant={tenant}|user={username}|{message}")
class OrgDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "org/dashboard.html"

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            tenant = self.request.user.tenant
            
            log_with_context(logging.INFO, "Accessing Organization Dashboard", self.request.user)
            
            context["total_depts"] = Department.objects.filter(tenant=tenant, 
        is_deleted=False).count()
            context["total_roles"] = JobRole.objects.filter(tenant=tenant).count()
            context["locations"] = Location.objects.filter(tenant=tenant).count()
            return context
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in OrgDashboardView: {str(e)}", self.request.user)
            return {}


# --- Structure ---

class OrgChartView(LoginRequiredMixin, TemplateView):
    template_name = "org/org_chart.html"

    def get_context_data(self, **kwargs):
        log_with_context(logging.INFO, "Viewing hierarchical Org Chart", self.request.user)
        context = super().get_context_data(**kwargs)
        context["roots"] = OrgUnit.objects.filter(
            tenant=self.request.user.tenant, parent__isnull=True
        )
        return context


class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = "org/department_list.html"
    context_object_name = "departments"

    def get_queryset(self):
        try:
            log_with_context(logging.INFO, "Listing all departments", self.request.user)
            return Department.objects.filter(tenant=self.request.user.tenant, 
        is_deleted=False).annotate(
                emp_count=Count("employees")
            )
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in DepartmentListView: {str(e)}", self.request.user)
            return Department.objects.none()


class DepartmentDetailView(LoginRequiredMixin, DetailView):
    model = Department
    template_name = "org/department_detail.html"
    context_object_name = "department"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        log_with_context(logging.INFO, f"Viewing Department Detail: {obj.name}", self.request.user)
        return obj


class LocationListView(LoginRequiredMixin, ListView):
    model = Location
    template_name = "org/location_list.html"
    context_object_name = "locations"

    def get_queryset(self):
        log_with_context(logging.INFO, "Accessing location directory", self.request.user)
        return Location.objects.filter(tenant=self.request.user.tenant)


# --- Job Roles ---

class JobRoleListView(LoginRequiredMixin, ListView):
    model = JobRole
    template_name = "org/job_role_list.html"
    context_object_name = "roles"

    def get_queryset(self):
        log_with_context(logging.INFO, "Accessing job role and grade list", self.request.user)
        return JobRole.objects.filter(tenant=self.request.user.tenant).order_by("role_type")


# --- Management ---

class CreateUnitView(LoginRequiredMixin, CreateView):
    model = OrgUnit
    template_name = "org/unit_form.html"
    fields = ["name", "parent", "unit_type", "head_of_unit"]
    success_url = reverse_lazy("org:org_chart")

    def form_valid(self, form):
        form.instance.tenant = self.request.user.tenant
        log_with_context(logging.INFO, f"Creating new OrgUnit: {form.instance.name} ({form.instance.unit_type})", self.request.user)
        return super().form_valid(form)


class UpdateUnitView(LoginRequiredMixin, UpdateView):
    model = OrgUnit
    template_name = "org/unit_form.html"
    fields = ["name", "parent", "head_of_unit"]
    success_url = reverse_lazy("org:org_chart")

    def form_valid(self, form):
        log_with_context(logging.INFO, f"Updating OrgUnit ID: {self.object.pk} ({self.object.name})", self.request.user)
        return super().form_valid(form)
    
    
    
    import logging
from django.urls import reverse_lazy
from django.views.generic import DeleteView
from django.contrib import messages

# Assuming log_with_context is defined in the same file or imported
# def log_with_context(level, message, user):
#     tenant = getattr(user, "tenant", None)
#     logger.log(
#         level,
#         f"tenant={tenant}|user={user.username}|{message}"
#     )

class DeleteUnitView(LoginRequiredMixin, DeleteView):
    model = OrgUnit
    template_name = "org/unit_confirm_delete.html"
    success_url = reverse_lazy("org:org_chart")

    def get_queryset(self):
        return OrgUnit.objects.filter(tenant=self.request.user.tenant)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_with_context(
            logging.WARNING, 
            f"DELETING OrgUnit: {obj.name} (ID: {obj.pk}, Type: {obj.unit_type})", 
            request.user
        )
        messages.success(request, f"Unit '{obj.name}' successfully deleted.")
        return super().delete(request, *args, **kwargs)


class DeleteDepartmentView(LoginRequiredMixin, DeleteView):
    model = Department
    template_name = "org/dept_confirm_delete.html"
    success_url = reverse_lazy("org:department_list")

    def get_queryset(self):
        return Department.objects.filter(tenant=self.request.user.tenant, 
        is_deleted=False)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_with_context(
            logging.WARNING, 
            f"DELETING Department: {obj.name} (ID: {obj.pk})", 
            request.user
        )
        messages.success(request, f"Department '{obj.name}' and its associations removed.")
        return super().delete(request, *args, **kwargs)


class DeleteJobRoleView(LoginRequiredMixin, DeleteView):
    model = JobRole
    template_name = "org/role_confirm_delete.html"
    success_url = reverse_lazy("org:job_role_list")

    def get_queryset(self):
        return JobRole.objects.filter(tenant=self.request.user.tenant)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_with_context(
            logging.WARNING, 
            f"DELETING JobRole: {obj.title} (Grade: {obj.grade})", 
            request.user
        )
        return super().delete(request, *args, **kwargs)


class DeleteLocationView(LoginRequiredMixin, DeleteView):
    model = Location
    success_url = reverse_lazy("org:location_list")

    def get_queryset(self):
        return Location.objects.filter(tenant=self.request.user.tenant)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_with_context(
            logging.WARNING, 
            f"DELETING Location: {obj.name} (ID: {obj.pk})", 
            request.user
        )
        return super().delete(request, *args, **kwargs)
    
    

class SoftDeleteUnitView(LoginRequiredMixin, View):
    """
    Handles soft-deletion by setting is_deleted=True instead of removing the row.
    """
    def post(self, request, pk):
        try:
            # Ensure tenant isolation
            unit = get_object_or_404(OrgUnit, pk=pk, tenant=request.user.tenant)
            
            unit.is_deleted = True
            unit.deleted_at = timezone.now()  # If you have this field
            unit.deleted_by = request.user
            unit.save()

            log_with_context(
                logging.WARNING, 
                f"SOFT-DELETE: OrgUnit '{unit.name}' (ID: {pk}) marked as deleted", 
                request.user
            )
            
            messages.warning(request, f"Unit '{unit.name}' has been deactivated.")
            return redirect("org:org_chart")

        except Exception as e:
            log_with_context(logging.ERROR, f"Soft-delete failed for OrgUnit {pk}: {str(e)}", request.user)
            messages.error(request, "Failed to deactivate the unit.")
            return redirect("org:org_chart")


class SoftDeleteJobRoleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        role = get_object_or_404(JobRole, pk=pk, tenant=request.user.tenant)
        
        role.is_active = False # Using is_active as the soft-delete toggle
        role.save()

        log_with_context(
            logging.WARNING, 
            f"SOFT-DELETE: JobRole '{role.title}' deactivated", 
            request.user
        )
        
        messages.info(request, f"Role '{role.title}' is no longer active.")
        return redirect("org:job_role_list")