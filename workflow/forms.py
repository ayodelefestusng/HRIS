from django.views.generic import FormView
from django import forms
from django.contrib.auth.models import Group
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin
from employees.models import Employee
from workflow.models import WorkflowInstance
from tinymce.widgets import TinyMCE
from .models import WorkflowInstance, Delegation, Workflow, InternalDocument
from org.models import OrgUnit
from workflow.services.workflow_service import WorkflowService

class InternalDocumentForm(forms.ModelForm):
    class Meta:
        model = InternalDocument
        fields = [
            'doc_type', 'subject', 'target_category', 'recipient', 'recipient_group', 
            'sender_unit', 'amount', 'content', 
            'attachment', 'reviewer', 'concurrence_list', 
            'approver_list', 'final_approver'
        ]
        widgets = {
            'doc_type': forms.Select(attrs={
                'class': 'form-select', 
                'hx-get': '/workflow/internal-document/fields/', 
                'hx-target': '#dynamic-fields',
                'hx-swap': 'innerHTML'
            }),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter subject...'}),
            'target_category': forms.Select(attrs={'class': 'form-select'}),
            'recipient': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., The Managing Director'}),
            'recipient_group': forms.Select(attrs={'class': 'form-select select2'}),
            'sender_unit': forms.Select(attrs={'class': 'form-control select2'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'content': TinyMCE(attrs={'cols': 80, 'rows': 30, 'class': 'form-control'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
            'reviewer': forms.Select(attrs={'class': 'form-control select2'}),
            'concurrence_list': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
            # 'concurrence_list': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
            # 'locations': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
             'approver_list': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
            
            
            # 'approver_list': forms.SelectMultiple(attrs={'class': 'form-control select2-users'}),
            'final_approver': forms.Select(attrs={'class': 'form-control select2'}),
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if tenant:
            # Filter querysets by tenant
            self.fields['sender_unit'].queryset = OrgUnit.objects.filter(tenant=tenant)
            emp_qs = Employee.objects.filter(tenant=tenant, is_active=True)
            self.fields['reviewer'].queryset = emp_qs
            self.fields['concurrence_list'].queryset = emp_qs
            
            # self.fields['concurrence_list'].queryset = emp_qs
            
            self.fields['approver_list'].queryset = emp_qs
            self.fields['final_approver'].queryset = emp_qs

class DelegationForm(forms.ModelForm):
    class Meta:
        model = Delegation
        fields = ["delegatee", "start_date", "end_date", "workflow_type"]
        widgets = {
            'delegatee': forms.Select(attrs={'class': 'form-control select2'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'workflow_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.delegator = kwargs.pop('delegator', None)
        super().__init__(*args, **kwargs)
        if self.delegator:
            service = WorkflowService(tenant=self.delegator.tenant)
            downline_ids = service.get_recursive_downline_ids(self.delegator)
            # Filter by downline and ensure they are active
            self.fields['delegatee'].queryset = Employee.objects.filter(
                id__in=downline_ids, 
                is_active=True
            ).exclude(id=self.delegator.id)
            
            # Also filter workflows by tenant
            self.fields['workflow_type'].queryset = Workflow.objects.filter(tenant=self.delegator.tenant)

class ReassignTaskForm(forms.Form):
    new_assignee = forms.ModelChoiceField(
        queryset=Employee.objects.none(),
        label="Select New Approver",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    reason = forms.CharField(widget=forms.Textarea, required=True)

class WorkflowReassignView(LoginRequiredMixin, FormView):
    template_name = "workflow/reassign_form.html"
    form_class = ReassignTaskForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        instance = get_object_or_404(WorkflowInstance, id=self.kwargs['pk'])
        service = WorkflowService(tenant=self.request.user.tenant)
        
        # Original approver logic
        original_approver = service.get_approver(instance, instance.current_stage).first()
        
        # Grand Manager can reassign to anyone in the original approver's downline
        downline_ids = service.get_recursive_downline_ids(original_approver)
        form.fields['new_assignee'].queryset = Employee.objects.filter(id__in=downline_ids, is_active=True)
        return form

    @transaction.atomic
    def form_valid(self, form):
        instance = get_object_or_404(WorkflowInstance, id=self.kwargs['pk'])
        new_approver = form.cleaned_data['new_assignee']
        reason = form.cleaned_data['reason']

        # Log the reassignment in history
        instance.track_history(
            actor=self.request.user.employee,
            description=f"REASSIGNED: Task moved from original approver to {new_approver.full_name}. Reason: {reason}"
        )
         
        # Implementation Detail: If you have a 'current_assignee' override field:
        # instance.manual_assignee = new_approver
        # instance.save()

        messages.success(self.request, f"Workflow reassigned to {new_approver.full_name}")
        return redirect('workflow:inbox')