from django import forms
from .models import (
    JobPosting, JobRole, Location, Candidate, CandidateSkillProfile, 
    Application, WorkExperience, Education
)
from org.models import JobTitle, State,  QualificationLevel, CompanyTier, CompanySize
from django.urls import reverse_lazy
from development.models import Skill
from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Interview, Application
from employees.models import Employee
from .models import Candidate
import logging

logger = logging.getLogger(__name__)
from tinymce.models import HTMLField
class JobPostingForm(forms.ModelForm):

    class Meta:
        model = JobPosting
        fields = ["role", "employment_type", "locations", "closing_date", "description", "requirements"]
        widgets = {
            'closing_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'id': 'id_description', 'rows': 5, 'class': 'form-control'}),
            'requirements': forms.Textarea(attrs={'id': 'id_requirements', 'rows': 5, 'class': 'form-control'}),
            'employment_type': forms.Select(attrs={'class': 'form-control'}),
            'locations': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
            'role': forms.Select(attrs={
                'class': 'form-select',
                'hx-get': reverse_lazy("ats:get_job_description"),
                'hx-trigger': 'change',
                'hx-target': '#role-blueprint-display',
            })
        }

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if not self.tenant:
            logger.error("JobPostingForm initialized without tenant context.")
            return

        try:
            # Filter unique JobTitles among vacant roles
            all_vacant = JobRole.objects.filter(
                tenant=self.tenant, vacant=True, is_deleted=False
            ).select_related('job_title')
            
            seen_titles = set()
            unique_ids = []
            for r in all_vacant:
                if r.job_title_id and r.job_title_id not in seen_titles:
                    unique_ids.append(r.id)
                    seen_titles.add(r.job_title_id)
            
            self.fields['role'].queryset = JobRole.objects.filter(id__in=unique_ids)
            
            # Location Filtering Logic based on Role
            role_id = self.data.get('role') or (self.instance.pk and self.instance.role_id)
            
            if role_id:
                selected_role = JobRole.objects.get(id=role_id, tenant=self.tenant)
                self.fields['locations'].queryset = Location.objects.filter(
                    org_units__roles__job_title=selected_role.job_title,
                    tenant=self.tenant
                ).distinct()
            else:
                self.fields['locations'].queryset = Location.objects.none()

        except Exception as e:
            # Log error but don't crash the whole page
            logger.error(f"Error initializing JobPostingForm: {str(e)}")
            self.fields['role'].queryset = JobRole.objects.none()
            self.fields['locations'].queryset = Location.objects.none()

        self.fields['role'].label_from_instance = lambda obj: f"{obj.job_title.name if obj.job_title else 'Unnamed Role'}"
class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ["application", "scheduled_at", "interviewers", "location"]
        widgets = {
            'scheduled_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'application': forms.Select(attrs={'class': 'form-control select2'}),
            'interviewers': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
            'location': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if self.tenant:
            self.fields['interviewers'].queryset = Employee.objects.filter(tenant=self.tenant)
            self.fields['application'].queryset = Application.objects.filter(tenant=self.tenant)
        
        self.fields['interviewers'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name}"

    def clean(self):
        cleaned_data = super().clean()
        scheduled_at = cleaned_data.get('scheduled_at')
        interviewers = cleaned_data.get('interviewers')

        if scheduled_at and interviewers:
            # We assume an interview lasts roughly 1 hour. 
            # We check for any interview starting 1 hour before or after the new time.
            start_window = scheduled_at - timedelta(minutes=59)
            end_window = scheduled_at + timedelta(minutes=59)

            for interviewer in interviewers:
                # Check if this specific interviewer is already booked
                conflicts = Interview.objects.filter(
                    tenant=self.tenant,
                    interviewers=interviewer,
                    scheduled_at__range=(start_window, end_window)
                ).exclude(pk=self.instance.pk) # Exclude self if we are editing

                if conflicts.exists():
                    conflict_time = conflicts.first().scheduled_at.strftime('%H:%M')
                    raise forms.ValidationError(
                        f"Conflict: {interviewer.first_name} {interviewer.last_name} "
                        f"is already scheduled for an interview at {conflict_time}."
                    )
        return cleaned_data



# forms.py
class CandidateApplicationForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['full_name', 'email', 'phone', 'resume']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John Doe'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'john@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+234...'}),
            'resume': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
        }
class InterviewForm1(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ["application", "scheduled_at", "interviewers"]
        widgets = {
            'scheduled_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'application': forms.Select(attrs={'class': 'form-control select2'}),
            # Ensure 'select2' class is present here
            'interviewers': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        }

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if self.tenant:
            self.fields['interviewers'].queryset = Employee.objects.filter(tenant=self.tenant)
            self.fields['application'].queryset = Application.objects.filter(tenant=self.tenant)
        
        self.fields['interviewers'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name}"

    def clean(self):
        cleaned_data = super().clean()
        scheduled_at = cleaned_data.get('scheduled_at')
        interviewers = cleaned_data.get('interviewers')

        if scheduled_at and interviewers:
            # Define a conflict window (e.g., 1 hour before and after)
            start_window = scheduled_at - timedelta(minutes=59)
            end_window = scheduled_at + timedelta(minutes=59)

            for interviewer in interviewers:
                conflicts = Interview.objects.filter(
                    interviewers=interviewer,
                    scheduled_at__range=(start_window, end_window)
                ).exclude(pk=self.instance.pk) # Exclude current interview if editing

                if conflicts.exists():
                    raise forms.ValidationError(
                        f"Conflict detected: {interviewer.first_name} {interviewer.last_name} "
                        f"is already scheduled for an interview around this time."
                    )
        return cleaned_data


# ===== ATS ADMIN FORMS =====

class CandidateAdminForm(forms.ModelForm):
    """Form for creating and editing candidates in the admin tool."""
    
    class Meta:
        model = Candidate
        fields = ['full_name', 'email', 'phone', 'resume', 'preferred_location', 'notes', 'tags', 'referred_by']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08012345678'}),
            'resume': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
            'preferred_location': forms.Select(attrs={'class': 'form-control select2'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'tags': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'referred_by': forms.Select(attrs={'class': 'form-control select2'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if self.tenant:
            self.fields['preferred_location'].queryset = Location.objects.filter(tenant=self.tenant)
            from .models import RecruiterTag
            self.fields['tags'].queryset = RecruiterTag.objects.filter(tenant=self.tenant)
            from employees.models import Employee
            self.fields['referred_by'].queryset = Employee.objects.filter(tenant=self.tenant)


class CandidateSkillProfileAdminForm(forms.ModelForm):
    """Form for managing candidate skill profiles."""
    
    class Meta:
        model = CandidateSkillProfile
        fields = ['candidate', 'skill', 'level']
        widgets = {
            'candidate': forms.Select(attrs={'class': 'form-control select2'}),
            'skill': forms.Select(attrs={'class': 'form-control select2'}),
            'level': forms.Select(attrs={'class': 'form-control'}, choices=[(i, f"Level {i}") for i in range(1, 6)]),
        }
    
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if self.tenant:
            self.fields['candidate'].queryset = Candidate.objects.filter(tenant=self.tenant)
            self.fields['skill'].queryset = Skill.objects.filter(tenant=self.tenant)


class ApplicationAdminForm(forms.ModelForm):
    """Form for managing applications."""
    
    class Meta:
        model = Application
        fields = ['candidate', 'job_posting', 'status', 'current_stage', 'ai_comments']
        widgets = {
            'candidate': forms.Select(attrs={'class': 'form-control select2'}),
            'job_posting': forms.Select(attrs={'class': 'form-control select2'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'current_stage': forms.Select(attrs={'class': 'form-control select2'}),
            'ai_comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'AI-generated insights...'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if self.tenant:
            self.fields['candidate'].queryset = Candidate.objects.filter(tenant=self.tenant)
            self.fields['job_posting'].queryset = JobPosting.objects.filter(tenant=self.tenant)
            from .models import RecruitmentStage
            self.fields['current_stage'].queryset = RecruitmentStage.objects.filter(tenant=self.tenant)


class WorkExperienceAdminForm(forms.ModelForm):
    """Form for managing work experience."""
    
    class Meta:
        model = WorkExperience
        fields = ['candidate', 'company_name', 'tier', 'size', 'start_date', 'end_date', 'previous_grade', 'manual_weight_override']
        widgets = {
            'candidate': forms.Select(attrs={'class': 'form-control select2'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'tier': forms.Select(attrs={'class': 'form-control'}),
            'size': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'previous_grade': forms.Select(attrs={'class': 'form-control select2'}),
            'manual_weight_override': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Optional manual weight'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if self.tenant:
            self.fields['candidate'].queryset = Candidate.objects.filter(tenant=self.tenant)
            self.fields['tier'].queryset = CompanyTier.objects.filter(tenant=self.tenant)
            self.fields['size'].queryset = CompanySize.objects.filter(tenant=self.tenant)
            from org.models import Grade
            self.fields['previous_grade'].queryset = Grade.objects.filter(tenant=self.tenant)


class EducationAdminForm(forms.ModelForm):
    """Form for managing education records."""
    
    class Meta:
        model = Education
        fields = ['candidate', 'institution', 'qualification']
        widgets = {
            'candidate': forms.Select(attrs={'class': 'form-control select2'}),
            'institution': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'University/Institution Name'}),
            'qualification': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if self.tenant:
            self.fields['candidate'].queryset = Candidate.objects.filter(tenant=self.tenant)
            self.fields['qualification'].queryset = QualificationLevel.objects.filter(tenant=self.tenant)