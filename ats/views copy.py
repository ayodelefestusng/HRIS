from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    View,
)
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse, request
from django.utils import timezone
from django.db.models import Count

from django.http import HttpResponse
from org.models import JobRole, Location

from ats.services.ranking_service import RankingService
from django.http import JsonResponse

import pdfplumber
import re
from development.models import Skill
from ats.models import CandidateSkillProfile
from .models import JobPosting, Candidate, Application, Interview, JobShareLink
from employees.models import Employee
import logging
from django.db import transaction
import logging
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import JobPostingForm, InterviewForm, CandidateApplicationForm
from django.db.models import Q, Max
from django.contrib.postgres.search import SearchVector
from .models import CandidateSkillProfile
import json

# views.py

from django.shortcuts import redirect
from django.contrib import messages
from .services.privacy_services import PrivacyService
from django.contrib.auth.decorators import login_required
import datetime
from .models import JobShareLink

logger = logging.getLogger(__name__)


def log_with_context(level, message, user):
    tenant = getattr(user, "tenant", None)
    logger.log(level, f"tenant={tenant}|user={user.username}|{message}")


# --- Job Posting ---
class PostJobView(LoginRequiredMixin, CreateView):
    model = JobPosting
    form_class = JobPostingForm  # Use the form class instead of 'fields'
    template_name = "ats/post_job.html"
    success_url = reverse_lazy("ats:manage_candidate")

    def get_form_kwargs(self):
        # Pass the tenant to the form so it can filter the roles/locations
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.user.tenant
        return kwargs

    def form_valid(self, form):
        form.instance.tenant = self.request.user.tenant
        # log_with_context(logging.INFO, f"Posted Form Instancw  -", self.request.user.tenant)

        return super().form_valid(form)

# views.py
from django.views.generic import ListView
from django.db.models import Count
from .models import JobPosting

class ManageJobsView(LoginRequiredMixin, ListView):
    model = JobPosting
    template_name = "ats/manage_jobs.html"
    context_object_name = "jobs"

    def get_queryset(self):
        # Only show jobs for the user's tenant, ordered by newest first
        return JobPosting.objects.filter(
            tenant=self.request.user.tenant,
            is_deleted=False
        ).select_related('role__job_title').annotate(
            applicant_count=Count('applications')
        ).order_by('-created_at')
# views.py


class JobBoardDetailPreview(LoginRequiredMixin, DetailView):
    model = JobPosting
    template_name = "ats/job_board_preview.html"
    context_object_name = "job"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = self.object.role

        # Pull requirements for display
        context["skills"] = role.skills.all()
        context["competencies"] = role.competencies.all()
        context["qualifications"] = role.required_qualifications.all()

        return context


class CandidateApplyView(CreateView):
    model = Candidate
    form_class = CandidateApplicationForm
    template_name = "ats/candidate_apply_form.html"

    def form_valid(self, form):
        job_id = self.kwargs.get("job_id")
        job_posting = get_object_or_404(JobPosting, id=job_id)

        with transaction.atomic():
            # 1. Save Candidate with Tenant from the Job
            candidate = form.save(commit=False)
            candidate.tenant = job_posting.tenant
            candidate.save()

            # 2. Create the Application record
            Application.objects.create(
                candidate=candidate,
                job_posting=job_posting,
                tenant=job_posting.tenant,
                status="APPLIED",
            )

            # 3. AUTO-POPULATE Skills from Job Requirements
            # This ensures the candidate is immediately ready for scoring
            role_skills = job_posting.role.skills.all()
            for rs in role_skills:
                CandidateSkillProfile.objects.get_or_create(
                    candidate=candidate,
                    skill=rs.skill_name,
                    tenant=job_posting.tenant,
                    defaults={"level": 1},  # Start at level 1 for evaluation
                )

            # 2. TRIGGER PARSER: Update levels based on resume text
            try:
                ResumeParserService.process_candidate_resume(candidate)
            except Exception as e:
                log_with_context(logging.ERROR, f"Parsing failed: {e}", request.user)
                # Log error but don't crash the application
                print(f"Parsing failed: {e}")
        return redirect("ats:application_success")


class ResumeParserService:
    @staticmethod
    def extract_text_from_pdf(pdf_file):
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + " "
        return text.lower()

    @staticmethod
    def calculate_skill_level(text, skill_name):
        """
        Heuristic: Look for years of experience mentioned near the skill.
        Example: 'Python (5 years)' or '6 years of experience in Java'
        """
        skill_name = skill_name.lower()
        # Find the skill in text, then look for numbers within the next 50 characters
        pattern = rf"{re.escape(skill_name)}.*?(\d+)\s*(?:years|yrs|year)"
        match = re.search(pattern, text)

        if match:
            years = int(match.group(1))
            if years >= 7:
                return 5  # Expert
            if years >= 5:
                return 4  # Advanced
            if years >= 3:
                return 3  # Intermediate
            return 2  # Junior
        return 1  # Default Found

    @classmethod
    def process_candidate_resume(cls, candidate):
        if not candidate.resume:
            return

        resume_text = cls.extract_text_from_pdf(candidate.resume)

        # Get all skill profiles we auto-populated during application
        profiles = CandidateSkillProfile.objects.filter(candidate=candidate)

        for profile in profiles:
            skill_name = profile.skill.name
            if skill_name.lower() in resume_text:
                new_level = cls.calculate_skill_level(resume_text, skill_name)
                profile.level = new_level
                profile.save()


# views.py


class JobLeaderboardView(LoginRequiredMixin, DetailView):
    model = JobPosting
    template_name = "ats/job_leaderboard.html"
    context_object_name = "job"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["leaderboard"] = RankingService.get_ranked_candidates(self.object)
        return context


# views.py
def manager_view_share(request, share_id):
    share = get_object_or_404(JobShareLink, id=share_id)

    if not share.is_valid():
        return render(request, "ats/share_expired.html", status=403)

    # Track views
    share.view_count += 1
    share.save()

    leaderboard = RankingService.get_ranked_candidates(share.job_posting)

    return render(
        request,
        "ats/manager_share_portal.html",
        {"job": share.job_posting, "leaderboard": leaderboard, "share": share},
    )


# views.py
@require_POST
def manager_feedback(request, share_id, candidate_id):
    share = get_object_or_404(JobShareLink, id=share_id, is_active=True)
    application = get_object_or_404(
        Application, candidate_id=candidate_id, job_posting=share.job_posting
    )

    # Update status to 'INTERVIEW_PENDING'
    application.status = "INTERVIEW"
    application.manager_recommendation = "APPROVED"
    application.save()

    # Log the event for the recruiter
    log_with_context(
        logging.INFO,
        f"Manager approved candidate {candidate_id} via share link",
        request.user,
    )

    return JsonResponse(
        {"status": "success", "next_step": "Recruiter notified for scheduling"}
    )
# views.py

@login_required
def generate_manager_share(request, job_id):
    job = get_object_or_404(JobPosting, id=job_id, tenant=request.user.tenant)
    
    share = JobShareLink.objects.create(
        job_posting=job,
        shared_by=request.user.employee,
        tenant=request.user.tenant
    )
    
    full_url = request.build_absolute_uri(
        reverse('ats:manager_view_share', kwargs={'share_id': share.id})
    )
    
    # Return as JSON for an HTMX/SweetAlert popup
    return JsonResponse({'share_url': full_url})

# views.py
def get_job_description(request):
    role_id = request.GET.get("role")
    tenant = request.user.tenant

    if not role_id:
        return HttpResponse("Select a role to see details.")

    role = (
        JobRole.objects.select_related("job_title")
        .prefetch_related(
            "required_qualifications", "skills__skill_name", "competencies__competency"
        )
        .get(id=role_id, tenant=tenant)
    )

    # We return a small HTML snippet that HTMX will swap into the description area
    # But we also include hidden data or specific formatting for the requirements
    context = {
        "role": role,
        "description": role.job_title.description if role.job_title else "",
        "qualifications": ", ".join(
            [q.name for q in role.required_qualifications.all()]
        ),
        "skills": role.skills.all(),
        "competencies": role.competencies.all(),
    }

    log_with_context(logging.INFO, f"Extracting JD ID: {role}", request.user)

    return render(request, "partials/role_info_snippet.html", context)


# views.py
@login_required
def job_preview(request):
    if request.method == "POST":
        # Extract data from the HTMX request
        role_id = request.POST.get("role")
        description = request.POST.get("description")
        requirements = request.POST.get("requirements")
        close_date = request.POST.get("closing_date")

        role = JobRole.objects.get(id=role_id) if role_id else None

        context = {
            "role": role,
            "description": description,
            "requirements": requirements,
            "closing_date": close_date,
            "today": datetime.date.today(),
        }
        return render(request, "ats/partials/job_post_preview_content.html", context)


# views.py
from django.shortcuts import render
from .forms import JobPostingForm


def job_preview_modal(request):
    # Initialize form with POST data to capture current user input
    form = JobPostingForm(request.POST, tenant=request.user.tenant)

    # Create a temporary instance (commit=False so it's not in DB)
    job = form.save(commit=False)

    # ManyToMany fields (locations) need special handling for unsaved instances
    # We fetch the actual location objects based on the IDs in the POST data
    location_ids = request.POST.getlist("locations")
    preview_locations = Location.objects.filter(id__in=location_ids)

    context = {"job": job, "preview_locations": preview_locations, "is_preview": True}
    return render(request, "ats/partials/job_preview_snippet.html", context)


class PublishJobView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            job = get_object_or_404(JobPosting, pk=pk, tenant=request.user.tenant)
            job.status = "OPEN"
            job.posted_at = timezone.now()
            job.save()

            # --- External Integrations (Mock) ---
            from .services.integration_service import IntegrationService

            linkedin_res = IntegrationService.post_job_to_linkedin(job)
            indeed_res = IntegrationService.post_job_to_indeed(job)

            log_with_context(
                logging.INFO,
                f"Job published: ID {pk} - {job.title}. "
                f"LinkedIn: {linkedin_res['status']}, Indeed: {indeed_res['status']}",
                request.user,
            )

            return JsonResponse(
                {
                    "status": "published",
                    "integrations": {"linkedin": linkedin_res, "indeed": indeed_res},
                }
            )

        except Exception as e:
            log_with_context(
                logging.ERROR, f"Error in PublishJobView: {str(e)}", request.user
            )
            return JsonResponse(
                {"status": "error", "message": "Failed to publish job."}, status=500
            )


class JobAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "ats/job_analytics.html"

    def get_context_data(self, **kwargs):
        log_with_context(logging.INFO, "Accessing JobAnalyticsView", self.request.user)
        context = super().get_context_data(**kwargs)
        tenant = self.request.user.tenant

        # 1. Applications Over Time (Last 6 Months)
        from django.db.models.functions import TruncMonth
        from django.db.models import Count
        import json
        import datetime

        six_months_ago = timezone.now() - datetime.timedelta(days=180)
        apps_over_time = (
            Application.objects.filter(tenant=tenant, submitted_at__gte=six_months_ago)
            .annotate(month=TruncMonth("submitted_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        labels = [x["month"].strftime("%b") for x in apps_over_time]
        data = [x["count"] for x in apps_over_time]

        context["chart_apps_labels"] = json.dumps(labels)
        context["chart_apps_data"] = json.dumps(data)

        # 2. Funnel Data (Group by Status)
        funnel_qs = (
            Application.objects.filter(tenant=tenant)
            .values("status")
            .annotate(count=Count("id"))
        )

        # Define standard order for the funnel
        stage_order = {
            "APPLIED": 1,
            "SCREENING": 2,
            "INTERVIEW": 3,
            "OFFER": 4,
            "HIRED": 5,
            "REJECTED": 6,
        }

        funnel_data_sorted = sorted(
            funnel_qs, key=lambda x: stage_order.get(x["status"], 99)
        )

        # Prepare colors based on status
        colors = []
        for item in funnel_data_sorted:
            s = item["status"]
            if s == "HIRED":
                colors.append("#82d616")  # Green
            elif s == "REJECTED":
                colors.append("#ea0606")  # Red
            elif s == "OFFER":
                colors.append("#17c1e8")  # Cyan
            else:
                colors.append("#cb0c9f")  # Purple/Default rules

        context["chart_funnel_labels"] = json.dumps(
            [x["status"] for x in funnel_data_sorted]
        )
        context["chart_funnel_data"] = json.dumps(
            [x["count"] for x in funnel_data_sorted]
        )
        context["chart_funnel_colors"] = json.dumps(colors)

        # 3. Key Metrics
        context["total_candidates"] = Application.objects.filter(tenant=tenant).count()
        context["active_jobs"] = JobPosting.objects.filter(
            tenant=tenant, status="OPEN"
        ).count()

        return context


# --- Resume Parsing ---


class ParseResumeView(LoginRequiredMixin, TemplateView):
    template_name = "ats/parse_resume.html"


class ExtractResumeInfoView(LoginRequiredMixin, View):
    def post(self, request, pk):
        log_with_context(
            logging.INFO, f"Extracting resume info for Candidate ID: {pk}", request.user
        )
        # Stub for AI resume parsing logic
        return JsonResponse(
            {
                "name": "John Doe",
                "skills": ["Python", "Django"],
                "email": "john@example.com",
            }
        )


# --- Candidate Management ---


class ManageCandidateView(LoginRequiredMixin, ListView):
    model = Application
    template_name = "ats/manage_candidates.html"
    context_object_name = "applications"

    def get_queryset(self):
        try:
            log_with_context(
                logging.INFO, "Loading candidate management board", self.request.user
            )
            return Application.objects.filter(
                tenant=self.request.user.tenant
            ).select_related("candidate", "job_posting")
        except Exception as e:
            log_with_context(
                logging.ERROR,
                f"Error in ManageCandidateView: {str(e)}",
                self.request.user,
            )
            return Application.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stages"] = [
            "APPLIED",
            "SCREENING",
            "INTERVIEW",
            "OFFER",
            "HIRED",
            "REJECTED",
        ]
        return context


class ViewCandidateProfileView1(LoginRequiredMixin, DetailView):
    model = Candidate
    template_name = "ats/candidate_profile.html"
    context_object_name = "candidate"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        log_with_context(
            logging.INFO,
            f"Viewing Candidate Profile: {obj.full_name} (ID: {obj.pk})",
            self.request.user,
        )
        return obj


class ViewCandidateProfileView(LoginRequiredMixin, DetailView):
    model = Candidate
    template_name = "ats/candidate_profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        candidate = self.get_object()

        # Prepare Spider Chart Data
        competencies = candidate.competency_profiles.all()
        context["spider_labels"] = json.dumps(
            [cp.competency.name for cp in competencies]
        )
        context["spider_values"] = json.dumps([cp.level for cp in competencies])

        # Communication History (Mockup - usually linked to an EmailLog model)
        # context['comms'] = EmailLog.objects.filter(candidate=candidate).order_by('-sent_at')

        return context


class ViewCandidateApplicationView(LoginRequiredMixin, DetailView):
    model = Application
    template_name = "ats/candidate_application.html"
    context_object_name = "application"

    def get_queryset(self):
        return Application.objects.filter(tenant=self.request.user.tenant)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        log_with_context(
            logging.INFO,
            f"Viewing Application ID: {obj.pk} for Job: {obj.job_posting.title}",
            self.request.user,
        )
        return obj


class AnonymizeCandidateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        # Safety check: Is the user an HR Manager?
        if not request.user.groups.filter(name="HR_Manager").exists():
            messages.error(
                request, "Unauthorized: Only HR Managers can anonymize data."
            )
            return redirect("ats:candidate_detail", pk=pk)

        success, msg = PrivacyService.anonymize_candidate(pk, request.user.tenant)
        if success:
            messages.success(
                request, "Candidate profile has been anonymized for GDPR compliance."
            )
        else:
            messages.error(request, msg)

        return redirect("ats:candidate_list")


class SearchCandidateView(LoginRequiredMixin, ListView):
    model = Candidate
    template_name = "ats/search_candidates.html"
    context_object_name = "candidates"

    def get_queryset(self):
        tenant = self.request.user.tenant
        queryset = Candidate.objects.filter(tenant=tenant).distinct()

        # 1. Basic Text Search (Name, Notes, Resume content)
        q = self.request.GET.get("q")
        log_with_context(
            logging.INFO, f"Searching candidates with query: '{q}'", self.request.user
        )
        if q:
            # If using Postgres, SearchVector is significantly more powerful than icontains
            queryset = queryset.filter(
                Q(full_name__icontains=q)
                | Q(notes__icontains=q)
                | Q(email__icontains=q)
            )

        # 2. Filter by Skill (Robust ATS logic)
        skill_id = self.request.GET.get("skill")
        min_level = self.request.GET.get("min_level", 1)
        if skill_id:
            queryset = queryset.filter(
                skill_profiles__skill_id=skill_id, skill_profiles__level__gte=min_level
            )

        # 3. Filter by Application Status
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(applications__status=status)

        # 4. Filter by Job ID
        job_id = self.request.GET.get("job_id")
        if job_id:
            queryset = queryset.filter(applications__job_posting__job_id=job_id)

        return queryset.select_related("preferred_location").prefetch_related(
            "skill_profiles__skill"
        )


class CandidateCommunicationView(LoginRequiredMixin, TemplateView):
    template_name = "ats/candidate_communication.html"


# --- Interview Scheduling ---
class ScheduleInterviewView(LoginRequiredMixin, CreateView):
    model = Interview
    form_class = InterviewForm
    template_name = "ats/schedule_interview.html"
    success_url = reverse_lazy("ats:manage_candidate")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.user.tenant
        return kwargs

    def form_valid(self, form):
        form.instance.tenant = self.request.user.tenant
        form.instance.setup_by = self.request.user.employee
        log_with_context(
            logging.INFO,
            f"Scheduling interview for Application ID: {form.instance.application.pk}",
            self.request.user,
        )

        return super().form_valid(form)


class NotifyCandidateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            interview = get_object_or_404(Interview, pk=pk, tenant=request.user.tenant)
            log_with_context(
                logging.INFO,
                f"Sending notification for Interview ID: {pk}",
                request.user,
            )
            return JsonResponse(
                {
                    "status": "sent",
                    "message": f"Email sent to {interview.application.candidate.email}",
                }
            )
        except Exception as e:
            log_with_context(
                logging.ERROR, f"Error in NotifyCandidateView: {str(e)}", request.user
            )
            return JsonResponse(
                {"status": "error", "message": "Failed to send notification."},
                status=500,
            )
