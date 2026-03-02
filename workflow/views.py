from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Exists, OuterRef, Subquery
from django.apps import apps
from django.forms import modelform_factory
import logging

from .forms import DelegationForm, InternalDocumentForm
from .models import (
    WorkflowInstance, Delegation, Workflow, InternalDocument, 
    Opportunity, Account, Contact, Vendor, Asset, ProcurementRequest
)
from workflow.services.workflow_service import WorkflowService
from workflow.services.dashboard_service import WorkflowDashboardService
from org.views import log_with_context
from employees.models import ProfileUpdateRequest
from development.models import EmployeeSkillProfile
from django_htmx.http import HttpResponseClientRefresh, HttpResponseClientRedirect
from django.http import HttpResponse
from django.views.generic import TemplateView, CreateView, UpdateView, DetailView

logger = logging.getLogger(__name__)



class WorkflowInboxView(LoginRequiredMixin, ListView):
    template_name = "workflow/inbox.html"
    context_object_name = "items"
    
    
    def get_queryset(self):
        user = self.request.user
        emp = user.employee
        
        # 1. Delegation Subquery (Keep this)
        delegations = Delegation.objects.filter(
            delegatee=emp,
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now(),
            workflow_type=OuterRef('workflow')
        ).values('id')

        # 2. Simple, Accurate Filter
        value = WorkflowInstance.objects.filter(
            tenant=user.tenant,
            completed_at__isnull=True,
            approval_status__iexact="pending"
        ).filter(
            Q(current_approvers=emp) | Q(Exists(delegations))
        ).select_related('current_stage', 'workflow', 'initiated_by').distinct().order_by('-created_at')

        log_with_context(logging.INFO, f"The details of the pending isntance {value}", self.request.user)
        return value
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            dashboard_service = WorkflowDashboardService(
                self.request.user.employee,
                self.request.user.tenant,
            )
            context["stats"] = dashboard_service.get_stats_summary()
            context["my_requests"] = WorkflowInstance.objects.filter(
                tenant=self.request.user.tenant, initiated_by=self.request.user.employee
            ).order_by("-created_at")[:50]

            log_with_context(logging.INFO, "Loaded Inbox Context", self.request.user)
            return context
        except Exception as e:
            # FIXED: Used logging.ERROR (Integer)
            log_with_context(
                logging.ERROR,
                f"Error in InboxView Context: {str(e)}",
                self.request.user,
            )
            context["error_message"] = "Unable to load dashboard stats."
            return context

    def get_stats(self, emp):
        """Calculates stats for the dashboard based on the logged-in employee."""
        return {
            'total_pending': WorkflowInstance.objects.filter(
                current_approvers=emp, 
                status__iexact='pending'
            ).count(),
            'overdue': WorkflowInstance.objects.filter(
                current_approvers=emp, 
                status__iexact='pending',
                created_at__lt=timezone.now() - timezone.timedelta(hours=24)
            ).count(),
        }

    def get_querysetv1(self):
        """Historical version, kept for reference but unused in main flow."""
        return WorkflowInstance.objects.none()







class WorkflowActionView(LoginRequiredMixin, View):
    """Handles the POST request for Approval or Rejection."""

    @transaction.atomic
    def post(self, request, pk):
        instance = get_object_or_404(WorkflowInstance, pk=pk, tenant=request.user.tenant)
        action = request.POST.get("action") # 'approve' or 'reject'
        comment = request.POST.get("comment", "")
        actor = request.user.employee
        service = WorkflowService(tenant=request.user.tenant)
        log_with_context(logging.INFO, f"Workflow alUKE {action} by {actor.full_name}", request.user)
        try:
            if action == "APP":
                # FIX: Pass 'instance' as the first argument
                service.track_history(instance, actor, f"Approved: {comment}", is_approved=True)
                service._move_to_next_stage(instance, actor)
                messages.success(request, "Request approved successfully.")
                
            elif action == "reject":
                # Using the new soft-rejection logic
                service.reject_to_initiator(instance, actor, comment)
                messages.warning(request, "Request has been sent back for amendment.")

            elif action == "resubmit":
                # Ensure ONLY the initiator can resubmit
                if instance.initiated_by != actor:
                    messages.error(request, "Unauthorized: Only the initiator can resubmit.")
                else:
                    service.resubmit_workflow(instance, actor)
                    messages.success(request, "Request resubmitted successfully to Stage 1.")

            log_with_context(logging.INFO, f"Workflow {action} by {actor.full_name}", request.user)
            
        except Exception as e:
            log_with_context(logging.ERROR, f"Action {action} failed: {str(e)}", request.user)
            messages.error(request, "An error occurred during the process.")

        # HTMX support: if it's an HTMX request, you might return a partial, 
        # otherwise redirect to inbox.
        if request.headers.get('HX-Request'):
            return HttpResponseClientRefresh() # Or redirect
        return redirect("workflow:inbox")



class WorkflowResubmitView(LoginRequiredMixin, UpdateView):
    template_name = "workflow/resubmit_form.html"
    
    def get_object(self, queryset=None):
        # We are actually editing the TARGET of the workflow, not the instance itself
        instance_id = self.kwargs.get('pk')
        self.workflow_instance = get_object_or_404(
            WorkflowInstance, pk=instance_id, initiated_by=self.request.user.employee
        )
        return self.workflow_instance.target

    def get_form_class(self):
        # Dynamically create a form for whatever model is being edited
        model = self.object.__class__
        # Exclude internal fields you don't want the user to touch during resubmission
        return modelform_factory(model, exclude=['tenant', 'status', 'created_at', 'updated_at'])

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # After saving the target changes, use the service to restart the workflow
        service = WorkflowService(tenant=self.request.user.tenant)
        service.resubmit_workflow(self.workflow_instance, self.request.user.employee)
        
        messages.success(self.request, "Changes saved and workflow restarted from Stage 1.")
        return response

    def get_success_url(self):
        return reverse("workflow:inbox")


def batch_workflow_action(request):
    if request.method == "POST":
        instance_ids = request.POST.getlist("instance_ids")
        action_code = request.POST.get("action")  # 'APP' or 'REJ'
        comment = request.POST.get("batch_comment", "Batch processed.")

        if not instance_ids:
            messages.warning(request, "No items were selected.")
            return redirect("workflow:inbox")

        try:
            with transaction.atomic():
                service = WorkflowService(tenant=request.user.tenant)
                results = service.batch_process(
                    instance_ids, request.user.employee, action_code, comment
                )

                success_count = len(results.get("success", []))
                fail_count = len(results.get("failed", []))

                if success_count:
                    messages.success(request, f"Successfully processed {success_count} requests.")
                    log_with_context(logging.INFO, f"Batch {action_code} success: {success_count}", request.user)
                
                if fail_count:
                    messages.error(request, f"Failed to process {fail_count} requests. Check logs.")
        
        except Exception as e:
            logger.error(f"Batch processing crash: {str(e)}")
            messages.error(request, "A system error occurred during batch processing.")

    return redirect("workflow:inbox")


def batch_workflow_actionv1(request):
    """
    Handles multiple approvals/rejections from the inbox checkboxes.
    """
    if request.method == "POST":
        instance_ids = request.POST.getlist("instance_ids")
        action_code = request.POST.get("action")  # 'APP' or 'REJ'
        comment = request.POST.get("batch_comment", "Batch processed by manager.")

        if not instance_ids:
            messages.warning(request, "No items were selected.")
            return redirect("workflow:inbox")

        service = WorkflowService(tenant=request.user.tenant)
        results = service.batch_process(
            instance_ids, request.user.employee, action_code, comment
        )

        success_count = len(results["success"])
        fail_count = len(results["failed"])

        if success_count:
            messages.success(
                request, f"Successfully processed {success_count} requests."
            )
        if fail_count:
            messages.error(
                request, f"Failed to process {fail_count} requests. Check logs."
            )

    return redirect("workflow:inbox")



class BatchActionView(LoginRequiredMixin, View):
    """
    Processes multiple workflow approvals or rejections in a single transaction.
    """
    def post(self, request, *args, **kwargs):
        instance_ids = request.POST.getlist('instance_ids')
        action = request.POST.get('action')  # e.g., 'APP' for Approve
        comment = request.POST.get('batch_comment', 'Batch processed by HR')

        if not instance_ids:
            messages.warning(request, "No items selected.")
            return redirect('workflow:inbox')

        success_count = 0
        fail_count = 0

        for inst_id in instance_ids:
            try:
                with transaction.atomic():
                    # select_for_update prevents race conditions during batch processing
                    instance = WorkflowInstance.objects.select_for_update().get(
                        id=inst_id, 
                        current_assignee=request.user
                    )
                    
                    if action == 'APP':
                        # This triggers the specific finalizer if it's the last stage
                        instance.approve(user=request.user, comment=comment)
                        success_count += 1
                    else:
                        instance.reject(user=request.user, comment=comment)
                        success_count += 1
                        
            except Exception as e:
                fail_count += 1
                logger.error(f"Batch processing failed for Instance {inst_id}: {str(e)}", exc_info=True)

        messages.success(request, f"Successfully processed {success_count} requests.")
        if fail_count > 0:
            messages.error(request, f"Failed to process {fail_count} requests. Check logs.")

        return redirect('workflow:inbox')

def confirm_resumption(request, pk):
    """
    Specific action for 'Block Leave' or standard leave to confirm the
    user is back. Moves status to 'leave_application' (Final State).
    """
    instance = get_object_or_404(WorkflowInstance, pk=pk, tenant=request.user.tenant)
    target = instance.target

    # Custom logic: Ensure they can only resume after start_date
    if target.start_date > timezone.now().date():
        messages.error(request, "Cannot confirm resumption before leave starts.")
        return redirect("workflow:detail", pk=pk)

    # Use the service to finalize
    service = WorkflowService(tenant=request.user.tenant)
    service.process_action(
        instance=instance,
        actor=request.user.employee,
        action_type="APP",
        comment="Employee has resumed duty as scheduled.",
    )

    messages.success(request, "Resumption confirmed. Workflow finalized.")
    return redirect("workflow:inbox")



class ProfileUpdateApprovalView(LoginRequiredMixin, DetailView):
    """
    Detailed view for HR/Managers to verify changes and see What-If impact.
    """
    model = ProfileUpdateRequest
    template_name = "workflow/approve_profile_update.html"
    context_object_name = "request_obj"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        req = self.object
        emp = req.employee

        # --- PARSE CHANGES ---
        proposed_skills = {}
        proposed_pii = {}
        if hasattr(req, 'proposed_data') and isinstance(req.proposed_data, dict):
            from development.models import Skill
            for key, value in req.proposed_data.items():
                try:
                    skill_id = int(key)
                    skill = Skill.objects.filter(id=skill_id).first()
                    skill_name = skill.name if skill else f"Skill ID {skill_id}"
                    proposed_skills[skill_name] = value
                except (ValueError, TypeError):
                    field_name = key.replace('_', ' ').capitalize()
                    proposed_pii[field_name] = value
        
        context['proposed_skills'] = proposed_skills
        context['proposed_pii'] = proposed_pii

        # --- WHAT-IF ANALYSIS ---
        try:
            # skills_only for calculate_fit expects {id: level}
            skills_only = {int(k): v for k, v in req.proposed_data.items() if k.isdigit()} if req.proposed_data else {}
            projected_fit = emp.calculate_fit(override_skills=skills_only)
            
            context['analysis'] = {
                'current_score': emp.last_fit_score or 0,
                'projected_score': projected_fit,
                'improvement': projected_fit - (emp.last_fit_score or 0)
            }
        except Exception as e:
            logger.error(f"What-If Analysis failed: {e}")
            context['analysis_error'] = "Could not calculate projected fit."

        return context


class FinalizeUpdateActionView(LoginRequiredMixin, View):
    """
    Finalizes a single Employee Update. 
    Moves data from ProfileUpdateRequest to production models.
    """
    def post(self, request, pk):
        try:
            with transaction.atomic():
                # 1. Fetch the Request
                req_obj = ProfileUpdateRequest.objects.select_for_update().get(
                    id=pk, 
                    tenant=request.user.tenant
                )
                emp = req_obj.employee

                # 2. Logic Check: Ensure it hasn't been finalized already
                if req_obj.status == 'leave_application':
                    messages.info(request, "This update has already been finalized.")
                    return redirect('workflow:inbox')

                # 3. Update PII Fields
                if req_obj.phone_number: emp.phone_number = req_obj.phone_number
                if req_obj.address: emp.address = req_obj.address
                if req_obj.next_of_kin: emp.next_of_kin = req_obj.next_of_kin
                
                emp.save()

                # 4. Skill Level Commits (HR Verified)
                if hasattr(req_obj, 'proposed_data') and isinstance(req_obj.proposed_data, dict):
                    for key, value in req_obj.proposed_data.items():
                        try:
                            skill_id = int(key)
                            EmployeeSkillProfile.objects.update_or_create(
                                employee=emp,
                                skill_id=skill_id,
                                tenant=request.user.tenant,
                                defaults={
                                    'level': value,
                                    'source': 'assessment',  # Marked as verified
                                    'comment': f"Verified by HR ({request.user.email}) via Workflow"
                                }
                            )
                        except (ValueError, TypeError):
                            continue

                # 5. Final State Transition
                req_obj.status = 'leave_application'
                req_obj.save()

                # 6. Clean Cache: Update Fit Score immediately after skill change
                # (Assuming FitCache logic exists as per instruction 5)
                emp.update_fit_cache()

                logger.info(f"Finalized Employee Update for {emp.full_name} [ID: {emp.id}]")
                messages.success(request, f"Profile for {emp.full_name} updated successfully.")

        except ProfileUpdateRequest.DoesNotExist:
            messages.error(request, "Request not found.")
        except Exception as e:
            logger.error(f"Finalization Error: {str(e)}", exc_info=True)
            messages.error(request, "A critical error occurred during finalization.")

        return redirect('workflow:inbox')


class InboxViewV1(LoginRequiredMixin, ListView):
    template_name = "workflow/inbox.html"
    context_object_name = "items"

    def get_queryset(self):
        try:
            # Use the DashboardService to find items needing THIS user's attention
            dashboard_service = WorkflowDashboardService(
                self.request.user.employee,
                self.request.user.tenant,
            )
            log_with_context(logging.INFO, "Accessing InboxView", self.request.user)
            return dashboard_service.get_pending_actions()

        except Exception as e:
            logger.error(f"Error in InboxView: {str(e)}", exc_info=True)
            # Always return an empty QuerySet of the expected model
            return WorkflowInstance.objects.none()

    def get_context_data(self, **kwargs):
        # Always initialize context first
        context = super().get_context_data(**kwargs)
        try:

            # 1. Stats
            dashboard_service = WorkflowDashboardService(
                self.request.user.employee,
                self.request.user.tenant,
            )
            context["stats"] = dashboard_service.get_stats_summary()

            # 2. "My Requests" (Items I initiated)
            # We can add pagination later if needed, but for now lists are fine since we use tables
            context["my_requests"] = WorkflowInstance.objects.filter(
                tenant=self.request.user.tenant, initiated_by=self.request.user.employee
            ).order_by("-created_at")[
                :50
            ]  # Limit to recent 50 for performance
            log_with_context(
                logging.INFO, "Creating Workflow Instance InboxView", self.request.user
            )
            return context
        except Exception as e:
            log_with_context(logging.ERROR, "Error in InboxView", self.request.user)
            logger.error(f"Error in InboxView: {str(e)}", exc_info=True)
            context["error_message"] = "Unable to load dashboard stats."
            return context


class HistoryView(LoginRequiredMixin, ListView):
    model = WorkflowInstance
    template_name = "workflow/history.html"
    context_object_name = "requests"

    def get_queryset(self):
        # Items initiated by me
        return WorkflowInstance.objects.filter(
            tenant=self.request.user.tenant, initiated_by=self.request.user.employee
        ).order_by("-created_at")


class WorkflowDetailView(LoginRequiredMixin, DetailView):
    model = WorkflowInstance
    template_name = "workflow/request_detail.html"
    context_object_name = "instance"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.object
        user_emp = self.request.user.employee
        service = WorkflowService(tenant=self.request.user.tenant)

        # 1. Permission Check: Is the current user an authorized approver?
        try:
            approvers = service.resolve_current_approvers(instance)
            context["is_approver"] = user_emp in approvers
            context["current_approovers"] = approvers
        except Exception as e:
            logger.error(f"Error resolving approvers in WorkflowDetailView: {e}")
            context["is_approver"] = False

        # 2. History & Audit Trail (Combine Narrative and Actions)
        # Using .history.all() for HistoricalRecord and .actions.all() for WorkflowAction
        narrative = list(instance.history.all())
        actions = list(instance.actions.all())
        
        # Merge and sort by timestamp/created_at
        # HistoricalRecord uses 'timestamp', WorkflowAction uses 'created_at'
        combined_trail = sorted(
            narrative + actions,
            key=lambda x: x.created_at,
            reverse=True
        )
        context["audit_trail"] = combined_trail

        # 3. Parse Proposed Changes (Skills vs PII)
        target = instance.target
        if hasattr(target, 'proposed_data') and isinstance(target.proposed_data, dict):
            skills_changes = {}
            pii_changes = {}
            from development.models import Skill
            
            for key, value in target.proposed_data.items():
                try:
                    skill_id = int(key)
                    skill = Skill.objects.filter(id=skill_id).first()
                    skill_name = skill.name if skill else f"Skill ID {skill_id}"
                    skills_changes[skill_name] = value
                except (ValueError, TypeError):
                    # It's a PII field
                    # Humanize field name
                    field_name = key.replace('_', ' ').capitalize()
                    pii_changes[field_name] = value
            
            context["proposed_skills"] = skills_changes
            context["proposed_pii"] = pii_changes

        log_with_context(logging.INFO, f"Viewed Workflow Detail {instance.id}", self.request.user)
        return context


class ProcessActionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        instance = get_object_or_404(
            WorkflowInstance, pk=pk, tenant=request.user.tenant
        )
        service = WorkflowService(request.user.tenant)

        action_type = request.POST.get("action")  # APP, REJ, COM, AMD
        comment = request.POST.get("comment", "")

        try:
            updated_instance, msg = service.process_action(
                instance=instance,
                actor=request.user.employee,
                action_type=action_type,
                comment=comment,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            messages.success(request, msg)
        except PermissionError:
            messages.error(request, "You are not authorized to perform this action.")
        except Exception as e:
            logger.error(f"Error in ProcessActionView: {str(e)}", exc_info=True)
            messages.error(request, "An unexpected error occurred.")

        return redirect("workflow:inbox")


class DelegateView(LoginRequiredMixin, CreateView):
    model = Delegation
    form_class = DelegationForm
    template_name = "workflow/delegate.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['delegator'] = self.request.user.employee
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_emp = self.request.user.employee
        
        # List of existing delegations
        search_query = self.request.GET.get('q', '')
        delegations = Delegation.objects.filter(delegator=user_emp).order_by('-start_date')
        
        if search_query:
            delegations = delegations.filter(
                Q(delegatee__first_name__icontains=search_query) |
                Q(delegatee__last_name__icontains=search_query) |
                Q(workflow_type__name__icontains=search_query)
            )
            
        context['delegations'] = delegations
        context['search_query'] = search_query
        return context

    def form_valid(self, form):
        try:
            form.instance.tenant = self.request.user.tenant
            form.instance.delegator = self.request.user.employee
            messages.success(self.request, "Delegation created successfully.")
            log_with_context(logging.INFO, "Created Delegation", self.request.user)
            return super().form_valid(form)
        except Exception as e:
            logger.error(f"Error creating delegation: {e}", exc_info=True)
            messages.error(self.request, "Failed to create delegation.")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("workflow:delegate") # Stay on page to see list
class ApprovalHubView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/approval_hub.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Approval Selection Hub"
        return context

class InternalDocumentCreateView(LoginRequiredMixin, CreateView):
    model = InternalDocument
    form_class = InternalDocumentForm
    template_name = "workflow/internal_document_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs

    def form_valid(self, form):
        form.instance.tenant = self.request.user.tenant
        form.instance.initiator = self.request.user.employee
        form.instance.doc_type = self.request.GET.get('type', 'MEMO').upper()
        
        with transaction.atomic():
            response = super().form_valid(form)
            # Automatically initiate workflow if needed, or leave it to a specific service
            service = WorkflowService(tenant=self.request.user.tenant)
            # Find or create a workflow for this doc type
            workflow = Workflow.objects.filter(
                tenant=self.request.user.tenant, 
                code=f"internal-{form.instance.doc_type.lower()}"
            ).first()
            
            if workflow:
                service.trigger_workflow(
                    workflow_code=workflow.code,
                    target=self.object,
                    started_by=self.request.user.employee
                )
                messages.success(self.request, f"{form.instance.get_doc_type_display()} initiated successfully.")
            else:
                messages.warning(self.request, f"{form.instance.get_doc_type_display()} created as draft. Workflow not configured.")
            
            return response

    def get_success_url(self):
        return reverse("workflow:inbox")

class InternalDocumentDetailView(LoginRequiredMixin, DetailView):
    model = InternalDocument
    template_name = "workflow/internal_document_detail.html"
    context_object_name = "doc"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if the user can see diffs (if they are the initiator and edited_content exists)
        context['show_diff'] = (
            self.object.initiator == self.request.user.employee and 
            self.object.reviewed_content and 
            self.object.reviewed_content != self.object.original_content
        )
        return context

class ReviewerEditView(LoginRequiredMixin, UpdateView):
    """
    Allows a reviewer to propose edits to the document.
    """
    model = InternalDocument
    form_class = InternalDocumentForm
    template_name = "workflow/reviewer_edit_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs

    def form_valid(self, form):
        # We save the edits but keep the original content for comparison
        form.instance.reviewed_content = form.cleaned_data['content']
        # We don't overwrite 'content' yet? Or do we? 
        # Usually, the reviewer's edit becomes the current 'content'
        # and the initiator reviews it later.
        response = super().form_valid(form)
        messages.success(self.request, "Your suggested edits have been saved.")
        return response

    def get_success_url(self):
        return reverse("workflow:inbox")

class CRMPipelineView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/crm_pipeline.html"

    def post(self, request, *args, **kwargs):
        action = request.GET.get('action')
        if action == 'move':
            opp_id = request.GET.get('id')
            to_stage = request.GET.get('to')
            try:
                opp = Opportunity.objects.get(pk=opp_id, tenant=request.user.tenant)
                # Instead of immediate update, trigger workflow
                opp.trigger_stage_transition(to_stage, request.user)
            except Opportunity.DoesNotExist:
                pass
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, 'tenant', None)
        
        # Group opportunities by stage
        stages = [choice[0] for choice in Opportunity.SALES_STAGE_CHOICES]
        pipeline = {stage: [] for stage in stages}
        
        opportunities = Opportunity.objects.filter(tenant=tenant).select_related('account', 'owner')
        for opp in opportunities:
            if opp.stage in pipeline:
                pipeline[opp.stage].append(opp)
        
        context['pipeline'] = pipeline
        context['stage_choices'] = Opportunity.SALES_STAGE_CHOICES
        return context

class ProcurementDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/procurement_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, 'tenant', None)
        
        context['vendors'] = Vendor.objects.filter(tenant=tenant)
        context['assets'] = Asset.objects.filter(tenant=tenant)
        context['requests'] = ProcurementRequest.objects.filter(tenant=tenant).select_related('linked_document', 'vendor')
        
        # Calculate total asset value
        total_value = sum(asset.purchase_price for asset in context['assets'])
        context['total_asset_value'] = total_value
        
        return context

def internal_document_fields(request):
    """
    HTMX view to return extra fields based on doc_type selection.
    """
    doc_type = request.GET.get('doc_type')
    form = InternalDocumentForm()
    
    html = ""
    if doc_type == 'EXPENSE':
        html = f"""
        <div class="mb-4 animate__animated animate__fadeIn">
            <label class="form-label h6 fw-bold">Amount</label>
            {form['amount']}
            <small class="text-muted">Enter the total reimbursement amount.</small>
        </div>
        """
    return HttpResponse(html)
