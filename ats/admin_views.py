"""
ATS Operations Admin Tool Views
Provides CRUD operations for ATS models with logging and error handling
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.db import transaction
from django.http import HttpResponse

from org.views import log_with_context
from .models import Candidate, CandidateSkillProfile, Application, WorkExperience, Education
from .forms import (
    CandidateAdminForm, CandidateSkillProfileAdminForm, ApplicationAdminForm,
    WorkExperienceAdminForm, EducationAdminForm
)

logger = logging.getLogger(__name__)


@login_required
def ats_admin_dashboard(request):
    """Main ATS admin operations dashboard."""
    try:
        tenant = request.user.tenant
        log_with_context(logging.INFO, "Accessing ATS Admin Dashboard", request.user)
        
        # Get overview stats
        context = {
            'candidate_count': Candidate.objects.filter(tenant=tenant).count(),
            'application_count': Application.objects.filter(tenant=tenant).count(),
            'work_exp_count': WorkExperience.objects.filter(tenant=tenant).count(),
            'education_count': Education.objects.filter(tenant=tenant).count(),
        }
        
        return render(request, 'ats/admin/dashboard.html', context)
    except Exception as e:
        log_with_context(logging.ERROR, f"Error loading ATS Admin Dashboard: {str(e)}", request.user)
        messages.error(request, f"Error loading dashboard: {str(e)}")
        return redirect('home')


# ===== CANDIDATE ADMIN VIEWS =====

class CandidateListView(LoginRequiredMixin, ListView):
    """List all candidates with pagination and search."""
    model = Candidate
    template_name = 'ats/admin/candidate_list.html'
    context_object_name = 'candidates'
    paginate_by = 20
    
    def get_queryset(self):
        tenant = self.request.user.tenant
        queryset = Candidate.objects.filter(tenant=tenant).select_related('preferred_location')
        
        # Search by name or email
        search_query = self.request.GET.get('search')
        if search_query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) | 
                Q(email__icontains=search_query)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        log_with_context(logging.INFO, "Viewing candidate list", self.request.user)
        return context


class CandidateCreateView(LoginRequiredMixin, CreateView):
    """Create a new candidate."""
    model = Candidate
    form_class = CandidateAdminForm
    template_name = 'ats/admin/candidate_form.html'
    success_url = reverse_lazy('ats:admin_candidate_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs
    
    def form_valid(self, form):
        try:
            form.instance.tenant = self.request.user.tenant
            response = super().form_valid(form)
            log_with_context(logging.INFO, f"Created new candidate: {form.instance.full_name}", self.request.user)
            messages.success(self.request, f"Candidate '{form.instance.full_name}' created successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error creating candidate: {str(e)}", self.request.user)
            messages.error(self.request, f"Error creating candidate: {str(e)}")
            return self.form_invalid(form)


class CandidateUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing candidate."""
    model = Candidate
    form_class = CandidateAdminForm
    template_name = 'ats/admin/candidate_form.html'
    success_url = reverse_lazy('ats:admin_candidate_list')
    
    def get_queryset(self):
        return Candidate.objects.filter(tenant=self.request.user.tenant)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            log_with_context(logging.INFO, f"Updated candidate: {form.instance.full_name}", self.request.user)
            messages.success(self.request, f"Candidate '{form.instance.full_name}' updated successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error updating candidate: {str(e)}", self.request.user)
            messages.error(self.request, f"Error updating candidate: {str(e)}")
            return self.form_invalid(form)


class CandidateDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a candidate."""
    model = Candidate
    template_name = 'ats/admin/candidate_confirm_delete.html'
    success_url = reverse_lazy('ats:admin_candidate_list')
    
    def get_queryset(self):
        return Candidate.objects.filter(tenant=self.request.user.tenant)
    
    def delete(self, request, *args, **kwargs):
        try:
            candidate_name = self.get_object().full_name
            response = super().delete(request, *args, **kwargs)
            log_with_context(logging.INFO, f"Deleted candidate: {candidate_name}", request.user)
            messages.success(request, f"Candidate '{candidate_name}' deleted successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error deleting candidate: {str(e)}", request.user)
            messages.error(request, f"Error deleting candidate: {str(e)}")
            return redirect('ats:admin_candidate_list')


# ===== CANDIDATE SKILL PROFILE ADMIN VIEWS =====

class SkillProfileListView(LoginRequiredMixin, ListView):
    """List all skill profiles."""
    model = CandidateSkillProfile
    template_name = 'ats/admin/skill_profile_list.html'
    context_object_name = 'profiles'
    paginate_by = 20
    
    def get_queryset(self):
        return CandidateSkillProfile.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('candidate', 'skill').order_by('-id')


class SkillProfileCreateView(LoginRequiredMixin, CreateView):
    """Create a new skill profile."""
    model = CandidateSkillProfile
    form_class = CandidateSkillProfileAdminForm
    template_name = 'ats/admin/skill_profile_form.html'
    success_url = reverse_lazy('ats:admin_skill_profile_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs
    
    def form_valid(self, form):
        try:
            form.instance.tenant = self.request.user.tenant
            response = super().form_valid(form)
            log_with_context(
                logging.INFO, 
                f"Added skill '{form.instance.skill}' to candidate '{form.instance.candidate}'",
                self.request.user
            )
            messages.success(self.request, "Skill profile created successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error creating skill profile: {str(e)}", self.request.user)
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


class SkillProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Update a skill profile."""
    model = CandidateSkillProfile
    form_class = CandidateSkillProfileAdminForm
    template_name = 'ats/admin/skill_profile_form.html'
    success_url = reverse_lazy('ats:admin_skill_profile_list')
    
    def get_queryset(self):
        return CandidateSkillProfile.objects.filter(tenant=self.request.user.tenant)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            log_with_context(logging.INFO, f"Updated skill profile", self.request.user)
            messages.success(self.request, "Skill profile updated successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error updating skill profile: {str(e)}", self.request.user)
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


class SkillProfileDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a skill profile."""
    model = CandidateSkillProfile
    template_name = 'ats/admin/skill_profile_confirm_delete.html'
    success_url = reverse_lazy('ats:admin_skill_profile_list')
    
    def get_queryset(self):
        return CandidateSkillProfile.objects.filter(tenant=self.request.user.tenant)
    
    def delete(self, request, *args, **kwargs):
        try:
            response = super().delete(request, *args, **kwargs)
            log_with_context(logging.INFO, "Deleted skill profile", request.user)
            messages.success(request, "Skill profile deleted successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error deleting skill profile: {str(e)}", request.user)
            messages.error(request, f"Error: {str(e)}")
            return redirect('ats:admin_skill_profile_list')


# ===== APPLICATION ADMIN VIEWS =====

class ApplicationListView(LoginRequiredMixin, ListView):
    """List all applications."""
    model = Application
    template_name = 'ats/admin/application_list.html'
    context_object_name = 'applications'
    paginate_by = 20
    
    def get_queryset(self):
        return Application.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('candidate', 'job_posting').order_by('-submitted_at')


class ApplicationUpdateView(LoginRequiredMixin, UpdateView):
    """Update an application."""
    model = Application
    form_class = ApplicationAdminForm
    template_name = 'ats/admin/application_form.html'
    success_url = reverse_lazy('ats:admin_application_list')
    
    def get_queryset(self):
        return Application.objects.filter(tenant=self.request.user.tenant)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            log_with_context(
                logging.INFO,
                f"Updated application status to {form.instance.status}",
                self.request.user
            )
            messages.success(self.request, "Application updated successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error updating application: {str(e)}", self.request.user)
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


# ===== WORK EXPERIENCE ADMIN VIEWS =====

class WorkExperienceListView(LoginRequiredMixin, ListView):
    """List all work experiences."""
    model = WorkExperience
    template_name = 'ats/admin/work_experience_list.html'
    context_object_name = 'experiences'
    paginate_by = 20
    
    def get_queryset(self):
        return WorkExperience.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('candidate', 'tier', 'size').order_by('-id')


class WorkExperienceCreateView(LoginRequiredMixin, CreateView):
    """Create a new work experience record."""
    model = WorkExperience
    form_class = WorkExperienceAdminForm
    template_name = 'ats/admin/work_experience_form.html'
    success_url = reverse_lazy('ats:admin_work_experience_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs
    
    def form_valid(self, form):
        try:
            form.instance.tenant = self.request.user.tenant
            response = super().form_valid(form)
            log_with_context(
                logging.INFO,
                f"Added work experience '{form.instance.company_name}' for '{form.instance.candidate}'",
                self.request.user
            )
            messages.success(self.request, "Work experience created successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error creating work experience: {str(e)}", self.request.user)
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


class WorkExperienceUpdateView(LoginRequiredMixin, UpdateView):
    """Update a work experience record."""
    model = WorkExperience
    form_class = WorkExperienceAdminForm
    template_name = 'ats/admin/work_experience_form.html'
    success_url = reverse_lazy('ats:admin_work_experience_list')
    
    def get_queryset(self):
        return WorkExperience.objects.filter(tenant=self.request.user.tenant)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            log_with_context(logging.INFO, f"Updated work experience", self.request.user)
            messages.success(self.request, "Work experience updated successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error updating work experience: {str(e)}", self.request.user)
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


class WorkExperienceDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a work experience record."""
    model = WorkExperience
    template_name = 'ats/admin/work_experience_confirm_delete.html'
    success_url = reverse_lazy('ats:admin_work_experience_list')
    
    def get_queryset(self):
        return WorkExperience.objects.filter(tenant=self.request.user.tenant)
    
    def delete(self, request, *args, **kwargs):
        try:
            response = super().delete(request, *args, **kwargs)
            log_with_context(logging.INFO, "Deleted work experience", request.user)
            messages.success(request, "Work experience deleted successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error deleting work experience: {str(e)}", request.user)
            messages.error(request, f"Error: {str(e)}")
            return redirect('ats:admin_work_experience_list')


# ===== EDUCATION ADMIN VIEWS =====

class EducationListView(LoginRequiredMixin, ListView):
    """List all education records."""
    model = Education
    template_name = 'ats/admin/education_list.html'
    context_object_name = 'educations'
    paginate_by = 20
    
    def get_queryset(self):
        return Education.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('candidate', 'qualification').order_by('-id')


class EducationCreateView(LoginRequiredMixin, CreateView):
    """Create a new education record."""
    model = Education
    form_class = EducationAdminForm
    template_name = 'ats/admin/education_form.html'
    success_url = reverse_lazy('ats:admin_education_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs
    
    def form_valid(self, form):
        try:
            form.instance.tenant = self.request.user.tenant
            response = super().form_valid(form)
            log_with_context(
                logging.INFO,
                f"Added education '{form.instance.qualification}' for '{form.instance.candidate}'",
                self.request.user
            )
            messages.success(self.request, "Education record created successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error creating education record: {str(e)}", self.request.user)
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


class EducationUpdateView(LoginRequiredMixin, UpdateView):
    """Update an education record."""
    model = Education
    form_class = EducationAdminForm
    template_name = 'ats/admin/education_form.html'
    success_url = reverse_lazy('ats:admin_education_list')
    
    def get_queryset(self):
        return Education.objects.filter(tenant=self.request.user.tenant)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            log_with_context(logging.INFO, f"Updated education record", self.request.user)
            messages.success(self.request, "Education record updated successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error updating education record: {str(e)}", self.request.user)
            messages.error(self.request, f"Error: {str(e)}")
            return self.form_invalid(form)


class EducationDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an education record."""
    model = Education
    template_name = 'ats/admin/education_confirm_delete.html'
    success_url = reverse_lazy('ats:admin_education_list')
    
    def get_queryset(self):
        return Education.objects.filter(tenant=self.request.user.tenant)
    
    def delete(self, request, *args, **kwargs):
        try:
            response = super().delete(request, *args, **kwargs)
            log_with_context(logging.INFO, "Deleted education record", request.user)
            messages.success(request, "Education record deleted successfully!")
            return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Error deleting education record: {str(e)}", request.user)
            messages.error(request, f"Error: {str(e)}")
            return redirect('ats:admin_education_list')
