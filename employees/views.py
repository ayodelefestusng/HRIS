from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, UpdateView, CreateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages

from development.models import EmployeeSkillProfile

from .models import (
    Employee,
    EmployeeDocument,
    CompanyPolicy,
    PolicyAcknowledgement,
    Benefit,
    EmployeeBenefit,
    ProfileUpdateRequest,
)
from .forms import ProfileUpdateForm
from workflow.models import Workflow, WorkflowInstance, WorkflowStage
from django.contrib.contenttypes.models import ContentType
from org.models import JobRole

from django.db.models import Q

import logging
from django.utils import timezone
from django.shortcuts import get_object_or_404, reverse
from django.http import JsonResponse,HttpResponseRedirect
from django.views.generic import ListView, DetailView, UpdateView, CreateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from workflow.services.workflow_service import get_recursive_downline_ids,WorkflowService
import logging
import json
from django.db import transaction
logger = logging.getLogger(__name__)


def log_with_context(level, message, user):
    tenant = getattr(user, "tenant", None)
    logger.log(level, f"tenant={tenant}|user={user.username}|{message}")


# --- Employee Profile ---



class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = "employees/employee_list.html"
    context_object_name = "employees"
    paginate_by = 20
    def get_queryset(self):
        user = self.request.user
        # Base queryset: strictly limited to the current tenant
        qs = Employee.objects.filter(tenant=user.tenant, is_deleted=False)
        manager_employee = user.employee
        service = WorkflowService(tenant=user.tenant)
        downline_ids = service.get_recursive_downline_ids(manager_employee)
        # 1. HR/Admin -> See everyone in tenant
        if user.is_hr_officer or user.is_hr_manager or user.is_hr_admin:
            return qs.prefetch_related("roles__org_unit")
        # 2. Manager -> See downline only
        elif user.is_manager:
            try:
                # Your iterative helper
                # downline_ids = get_recursive_downline_ids(manager_employee)
                
                # Include self in the viewable list
                downline_ids.append(manager_employee.id) 
                return qs.filter(id__in=downline_ids).prefetch_related("roles__org_unit")
            except Employee.DoesNotExist:
                return qs.none()

        # 3. Regular Employee -> See only self
        return qs.filter(user=user).prefetch_related("roles__org_unit")
    
    def get_querysetv1(self):
        user = self.request.user
        log_with_context(logging.INFO, "Accessing employee directory", user)
        
        # Base Queryset
        qs = Employee.objects.filter(
            tenant=user.tenant, 
            is_deleted=False
        ).prefetch_related("roles__org_unit", "roles__job_title")

        # 1. HR Officer / HR Manager / HR Admin -> Full list
        if user.is_hr_officer or user.is_hr_manager or user.is_hr_admin:
            pass 

        # 2. Manager -> Recursive Downline
        elif user.is_manager:
            try:
                manager_employee = user.employee
                # Get the IDs of everyone reporting to this manager at any level
                # downline_ids = self.get_recursive_downline_ids(manager_employee)
                downline_ids = get_recursive_downline_ids(manager_employee)
                log_with_context(logging.INFO, f"Searching employees with query: {downline_ids}", self.request.user)

                qs = qs.filter(id__in=downline_ids)
            except Employee.DoesNotExist:
                qs = qs.none()

        # 3. Otherwise -> Personal record
        else:
            qs = qs.filter(user=user)

        # Apply Search Logic
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) | 
                Q(last_name__icontains=q) | 
                Q(employee_id__icontains=q)
            )

        for emp in qs:
            emp.primary_role = emp.roles.first()

        return qs

    def get_recursive_downline_ids1(self, employee):
        """Helper to fetch all IDs in the reporting chain."""
        full_ids = []
        # Start with direct reports
        stack = list(Employee.objects.filter(line_manager=employee).values_list('id', flat=True))
        
        while stack:
            current_id = stack.pop()
            if current_id not in full_ids:
                full_ids.append(current_id)
                # Find reports of this person and add to stack
                child_reports = Employee.objects.filter(line_manager_id=current_id).values_list('id', flat=True)
                stack.extend(child_reports)
                log_with_context(logging.INFO, f"Searching employees with query: {current_id}", self.request.user)
        
        return full_ids
    
    def get_queryset1(self):
        log_with_context(logging.INFO, "Accessing employee directory", self.request.user)
        qs = Employee.objects.filter(tenant=self.request.user.tenant).prefetch_related("roles__org_unit")

        q = self.request.GET.get("q")
        if q:
            log_with_context(logging.INFO, f"Searching employees with query: {q}", self.request.user)
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q))

        # Attach primary_role to each employee
        for emp in qs:
            emp.primary_role = emp.roles.first()

        return qs


class EmployeeDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = "employees/employee_detail.html"
    context_object_name = "employee"

    def get_queryset1(self):
        return Employee.objects.prefetch_related("roles__org_unit")
    
    def get_queryset(self):
        user = self.request.user
        qs = Employee.objects.filter(tenant=user.tenant, is_deleted=False).prefetch_related("roles__org_unit")
        manager_employee = user.employee
        service = WorkflowService(tenant=user.tenant)
        downline_ids = service.get_recursive_downline_ids(manager_employee)
        # 1. HR Roles -> Full Access
        if user.is_hr_officer or user.is_hr_manager or user.is_hr_admin:
            pass

        # 2. Manager -> Recursive Downline
        elif user.is_manager:
            try:
                qs = qs.filter(id__in=downline_ids)
            except Employee.DoesNotExist:
                qs = qs.none()

        # 3. Otherwise -> Personal Record
        else:
            qs = qs.filter(user=user)

        # Apply Search
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) | 
                Q(last_name__icontains=q) | 
                Q(employee_id__icontains=q)
            )

        for emp in qs:
            emp.primary_role = emp.roles.first()

        return qs

    def get_recursive_downline_ids(self, employee):
        """Helper to fetch all IDs in the reporting chain."""
        full_ids = []
        stack = list(Employee.objects.filter(line_manager=employee).values_list('id', flat=True))
        
        while stack:
            current_id = stack.pop()
            if current_id not in full_ids:
                full_ids.append(current_id)
                child_reports = Employee.objects.filter(line_manager_id=current_id).values_list('id', flat=True)
                stack.extend(child_reports)
        
        return full_ids

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        log_with_context(
            logging.INFO, 
            f"Profile Access: {self.request.user.email} viewed {obj.full_name}'s record.", 
            self.request.user
        )
        # Attach primary_role for detail view
        obj.primary_role = obj.roles.first()
        return obj
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Logic: Check if this specific employee has a pending profile update
        pending_request = ProfileUpdateRequest.objects.filter(
            employee=self.object, 
            approval_status='pending'
        ).first()

        if pending_request:
            context['has_pending_update'] = True
            # Find the workflow instance to provide a direct link to the inbox item
            context['pending_workflow_id'] = WorkflowInstance.objects.filter(
                object_id=pending_request.id,
                content_type=ContentType.objects.get_for_model(ProfileUpdateRequest)
            ).values_list('id', flat=True).first()
            
        return context
class EmployeeUpdateView(LoginRequiredMixin, UpdateView):
    model = Employee
    template_name = "employees/employee_form.html" # UNCOMMENT THIS
    fields = [                                     # UNCOMMENT THIS
        "first_name", "last_name", "personal_email", 
        "phone_number", "address", "date_of_birth", "gender",
    ]

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        
        if not form.is_valid():
            return self.form_invalid(form)

        user = request.user
        service = WorkflowService(tenant=user.tenant)
        is_hr = any([user.is_hr_admin, user.is_hr_manager, user.is_hr_officer])

        try:
            if is_hr:
                self.object = form.save()
                self.process_immediate_skills(request)
                log_with_context(logging.INFO, f"HR Direct Update for {self.object.full_name}", user)
                return HttpResponseRedirect(self.get_success_url())
            
            # --- EMPLOYEE WORKFLOW LOGIC ---
            if ProfileUpdateRequest.objects.filter(employee=self.object, approval_status='pending').exists():
                messages.warning(request, "A pending update request already exists.")
                return redirect('workflow:inbox')

            with transaction.atomic():
                update_request = ProfileUpdateRequest.objects.create(
                    employee=self.object,
                    tenant=user.tenant,
                    phone_number=form.cleaned_data.get('phone_number'),
                    address=form.cleaned_data.get('address'),
                    proposed_data=self.get_proposed_skills_dict(request),
                    approval_status='pending'
                )

                # Use Service Method instead of local model creation
                service.trigger_workflow(
                    workflow_code='profile-update',
                    target=update_request,
                    started_by=request.user.employee
                )

            messages.success(request, "Change request submitted for approval.")
            return HttpResponseRedirect(self.get_success_url())

        except Exception as e:
            logger.error(f"Employee update failed for {user.username}: {str(e)}", exc_info=True)
            messages.error(request, f"System error during update: {str(e)}")
            return self.form_invalid(form)

    def process_immediate_skills(self, request):
        """Helper for HR immediate updates."""
        for profile in self.object.skill_profiles.all():
            skill_id = f"skill_{profile.skill.id}"
            if skill_id in request.POST:
                profile.level = int(request.POST[skill_id])
                profile.save()

    def get_proposed_skills_dict(self, request):
        """Extracts skill levels from POST without saving them."""
        proposed = {}
        for profile in self.object.skill_profiles.all():
            skill_id = f"skill_{profile.skill.id}"
            if skill_id in request.POST:
                proposed[str(profile.skill.id)] = int(request.POST[skill_id])
        return proposed

    def trigger_workflow(self, update_req):
        """Initiates the actual workflow instance."""
        workflow = Workflow.objects.get(code='profile-update', tenant=self.request.user.tenant)
        WorkflowInstance.objects.create(
            workflow=workflow,
            target=update_req,
            current_stage=workflow.stages.order_by('sequence').first(),
            initiated_by=self.request.user.employee,
            tenant=self.request.user.tenant
        )
    def get_success_url(self):
        return reverse("employees:employee_detail", kwargs={"pk": self.object.pk})
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch existing skills for the employee being edited
        context['current_skills'] = self.object.skill_profiles.select_related('skill')
        return context
    
       
 
class ProfileUpdateRequestView(LoginRequiredMixin, CreateView):
    model = ProfileUpdateRequest
    form_class = ProfileUpdateForm
    template_name = "employees/request_update.html"

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            # 1. Prepare Proposed Skills from POST data instead of creating records
            proposed_skills = {}
            
            # Get existing skill levels being modified
            for key, value in request.POST.items():
                if key.startswith("skill_"):
                    skill_id = key.replace("skill_", "")
                    proposed_skills[skill_id] = int(value)
            
            # 2. Add New Skills from the JSON field
            new_skills_data = request.POST.get("new_skills", "{}")
            try:
                new_skills_dict = json.loads(new_skills_data)
                proposed_skills.update(new_skills_dict)
            except json.JSONDecodeError:
                pass

            # 3. Save the request with the proposed data
            profile_request = form.save(commit=False)
            profile_request.employee = request.user.employee
            profile_request.tenant = request.user.tenant
            profile_request.proposed_data = proposed_skills # Store for later
            profile_request.status = 'pending'
            profile_request.save()

            # 4. Trigger the Workflow Instance
            self.initiate_workflow(profile_request)

            return redirect(self.get_success_url())
        return self.form_invalid(form)

    def initiate_workflow(self, target_obj):
        # Implementation of workflow instance creation as discussed previously
        workflow = Workflow.objects.get(code='profile-update', tenant=self.request.user.tenant)
        WorkflowInstance.objects.create(
            workflow=workflow,
            target=target_obj,
            current_stage=workflow.stages.order_by('sequence').first(),
            initiated_by=self.request.user.employee,
            tenant=self.request.user.tenant
        )

      
       
        
class EmployeeUpdateViewv1(LoginRequiredMixin, UpdateView):
    model = Employee
    # template_name = "employees/employee_form.html"
    # fields = [
    #     "first_name",
    #     "last_name",
    #     "personal_email",
    #     "phone_number",
    #     "address",
    #     "date_of_birth",
    #     "gender",
    # ]
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        # Allow HR but redirect regular employees to the Request Workflow
        is_hr = any([user.is_hr_admin, user.is_hr_manager, user.is_hr_officer])
        
        if not is_hr:
            messages.info(request, "Direct updates are disabled. Please submit a Change Request.")
            return redirect(reverse("employees:request_update"))
            
        return super().dispatch(request, *args, **kwargs)
    def form_valid(self, form):
        log_with_context(logging.INFO, "UPDATEING", self.request.user)
        log_with_context(logging.INFO, f"Updating profile for employee ID: {self.object.pk}", self.request.user)
        return super().form_valid(form)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch existing skills for the employee being edited
        context['current_skills'] = self.object.skill_profiles.select_related('skill')
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        
        if form.is_valid():
            # 1. Save the main form (personal info)
            self.object = form.save()
            
            # 2. Process Skill Updates
            skill_profiles = self.object.skill_profiles.all()
            for profile in skill_profiles:
                skill_id = str(profile.skill.id)
                if f"skill_{skill_id}" in request.POST:
                    new_level = int(request.POST[f"skill_{skill_id}"])
                    profile.level = new_level
                    profile.save()
                    log_with_context(logging.INFO, f"Updated skill {profile.skill.name} to {new_level} for {self.object.first_name}", request.user)
            
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("employees:employee_detail", kwargs={"pk": self.object.pk})




class ProfileUpdateRequestViewv1(LoginRequiredMixin, CreateView):
    model = ProfileUpdateRequest
    form_class = ProfileUpdateForm
    template_name = "employees/profile_update_request.html"

    def form_valid(self, form):
        form.instance.tenant = self.request.user.tenant
        form.instance.employee = self.request.user.employee

        # 1. Save the Request (Staging)
        response = super().form_valid(form)

        # 2. Initiate Workflow
        try:
            workflow = Workflow.objects.get(
                code="profile-update", tenant=self.request.user.tenant
            )
            first_stage = workflow.stages.order_by("sequence").first()

            if not first_stage:
                raise ValueError("Workflow has no stages")

            instance = WorkflowInstance.objects.create(
                tenant=self.request.user.tenant,
                workflow=workflow,
                content_type=ContentType.objects.get_for_model(ProfileUpdateRequest),
                object_id=self.object.pk,
                current_stage=first_stage,
                initiated_by=self.request.user.employee,
            )

            # Link workflow back to request
            self.object.workflow_instance = instance
            self.object.save()

            log_with_context(
                logging.INFO,
                f"Initiated Profile Update Workflow for {self.request.user}",
                self.request.user,
            )

        except Workflow.DoesNotExist:
            # Fallback: Just save request but warn/log (or auto-approve if desired, but sticking to logic)
            log_with_context(
                logging.ERROR,
                "Profile Update Workflow definition not found!",
                self.request.user,
            )
            # Optionally message user

        return response

    def get_success_url(self):
        return reverse("workflow:inbox")


# --- Documents ---


class DocumentListView(LoginRequiredMixin, ListView):
    model = EmployeeDocument
    template_name = "employees/document_list.html"
    context_object_name = "documents"

    def get_queryset(self):
        log_with_context(
            logging.INFO,
            f"Viewing document list for employee ID: {self.kwargs['pk']}",
            self.request.user,
        )
        return EmployeeDocument.objects.filter(
            tenant=self.request.user.tenant, employee_id=self.kwargs["pk"]
        )


class UploadDocumentView(LoginRequiredMixin, CreateView):
    model = EmployeeDocument
    template_name = "employees/upload_document.html"
    fields = ["document_type", "file", "description", "expiry_date"]

    def form_valid(self, form):
        form.instance.tenant = self.request.user.tenant
        employee = get_object_or_404(
            Employee, pk=self.kwargs["pk"], tenant=self.request.user.tenant
        )
        form.instance.employee = employee
        log_with_context(
            logging.INFO,
            f"Uploading {form.instance.document_type} for employee {employee.pk}",
            self.request.user,
        )
        return super().form_valid(form)


# --- Policies ---


class PolicyListView(LoginRequiredMixin, ListView):
    model = CompanyPolicy
    template_name = "employees/policy_list.html"
    context_object_name = "policies"

    def get_queryset(self):
        log_with_context(logging.INFO, "Viewing company policies", self.request.user)
        return CompanyPolicy.objects.filter(
            tenant=self.request.user.tenant, is_active=True
        )


class AcknowledgePolicyView(LoginRequiredMixin, View):
    def post(self, request, pk):
        policy = get_object_or_404(CompanyPolicy, pk=pk, tenant=request.user.tenant)
        employee = request.user.employee

        log_with_context(
            logging.INFO, f"Acknowledging policy: {policy.title}", request.user
        )
        PolicyAcknowledgement.objects.get_or_create(
            tenant=request.user.tenant,
            policy=policy,
            employee=employee,
            defaults={"acknowledged_at": timezone.now()},
        )
        return JsonResponse({"status": "acknowledged"})


# --- Benefits ---


class BenefitsListView(LoginRequiredMixin, ListView):
    model = Benefit
    template_name = "employees/benefit_list.html"
    context_object_name = "benefits"

    def get_queryset(self):
        log_with_context(logging.INFO, "Viewing available benefits", self.request.user)
        return Benefit.objects.filter(tenant=self.request.user.tenant, is_active=True)


class EnrollBenefitView(LoginRequiredMixin, View):
    def post(self, request, pk):
        benefit = get_object_or_404(Benefit, pk=pk, tenant=request.user.tenant)
        employee = request.user.employee

        log_with_context(
            logging.INFO, f"Enrolling in benefit: {benefit.name}", request.user
        )
        EmployeeBenefit.objects.create(
            tenant=request.user.tenant,
            employee=employee,
            benefit=benefit,
            start_date=timezone.now().date(),
        )
        return JsonResponse(
            {"status": "enrolled", "message": f"Enrolled in {benefit.name}"}
        )
