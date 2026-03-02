import logging
import datetime
import json
import re
import pdfplumber
import threading  # For simple async-style background parsing

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.utils import log, timezone
from django.db import transaction, DatabaseError
from django.db.models import Q, Max, Count
from django.db.models.functions import TruncMonth
from django.contrib import messages


# views.py
from django.utils.dateparse import parse_datetime
from django.contrib import messages

from workflow.services.workflow_service import log_with_context, RankingService, ResumeParserService, PrivacyService
from ats.services.ats_services import InterviewScheduler


# Local model and form imports
from .models import JobPosting, Candidate, Application, Interview, JobShareLink, CandidateSkillProfile
from .forms import JobPostingForm, InterviewForm, CandidateApplicationForm
from org.models import JobRole, Location
from employees.models import Employee
import logging
import datetime
import json
import re
import pdfplumber
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db import transaction, DatabaseError
from django.db.models import Q, Count
from django.db.models.functions import TruncMonth
from django.contrib import messages

# Model/Form Imports
from .models import JobPosting, Candidate, Application, Interview, JobShareLink, CandidateSkillProfile
from .forms import JobPostingForm, InterviewForm, CandidateApplicationForm
from org.models import JobRole, Location

from .tasks import process_resume_async  # The Celery Task
from workflow.services.workflow_service import ResumeParserService,IntegrationService
logger = logging.getLogger(__name__)

from org.views import log_with_context
# --- HELPERS & SERVICES ---

# def log_with_context(level, message, user):
#     """Utility for structured logging with tenant context."""
#     tenant = getattr(user, "tenant", None) if user else "Anonymous"
#     logger.log(level, f"tenant={tenant}|user={user}|{message}")


# --- JOB POSTING & MANAGEMENT ---
# --- JOB POSTING & MANAGEMENT ---
import requests 
from django.http import JsonResponse 
from django.conf import settings
import requests
from django.http import JsonResponse

from django.shortcuts import redirect
from django.conf import settings
from datetime import timedelta
import requests
from org.models import LinkedInIntegration
from django.shortcuts import redirect
from django.http import JsonResponse
from django.conf import settings

# --- LOGIN ---




# --- ACCOUNT & INTEGRATION ---

@login_required
def linkedin_login(request):
    """
    Redirect user to LinkedIn OAuth2 login for the current tenant.
    """
    tenant = request.user.tenant
    integration = get_object_or_404(LinkedInIntegration, tenant=tenant)

    log_with_context(logging.INFO, "User initializing LinkedIn login", request.user)

    scopes = "openid profile email w_member_social"
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={integration.client_id}"
        f"&redirect_uri={integration.redirect_uri}"
        f"&scope={scopes.replace(' ', '%20')}"
    )

    return redirect(auth_url)


@login_required
def linkedin_callback(request):
    """
    Handle LinkedIn OAuth2 callback.
    Exchange authorization code for access token.
    """
    code = request.GET.get("code")
    if not code:        
        log_with_context(logging.ERROR, "No code returned from LinkedIn", request.user) 
        return JsonResponse({"error": "No code returned from LinkedIn"}, status=400)
    
    tenant = request.user.tenant
    
    try:
        from ats.services.ats_services import IntegrationService
        
        # We need to manually handle the initial token exchange because it's slightly different 
        # from the refresh logic, OR we could build an exchange method in the service.
        # For now, let's keep the initial exchange here but use the integration object.
        integration = LinkedInIntegration.objects.get(tenant=tenant)
        
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": integration.redirect_uri,
            "client_id": integration.client_id,
            "client_secret": integration.client_secret,
        }
        
        response = requests.post(token_url, data=data)
        token_data = response.json() 
        access_token = token_data.get("access_token") 
        refresh_token = token_data.get("refresh_token") 
        expires_in = token_data.get("expires_in")
        
        if not access_token: 
             log_with_context(logging.ERROR, f"Failed to get access token: {token_data}", request.user)
             return JsonResponse({"error": "Failed to get access token"}, status=400)

        # Save tokens
        integration.access_token = access_token 
        integration.refresh_token = refresh_token
        integration.expires_at = timezone.now() + timedelta(seconds=expires_in)
        integration.save()
        
        log_with_context(logging.INFO, f"LinkedIn tokens updated for tenant {tenant}", request.user) 
        return JsonResponse({"status": "success", "message": "LinkedIn integration successful", "expires_in": expires_in}) 
        
    except Exception as e:
        log_with_context(logging.ERROR, f"LinkedIn callback failed: {e}", request.user)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

def refresh_linkedin_token(integration: LinkedInIntegration):
    if integration.is_token_valid():
        return integration.access_token

    refresh_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": integration.refresh_token,
        "client_id": integration.client_id,
        "client_secret": integration.client_secret,
    }
    response = requests.post(refresh_url, data=data).json()

    integration.access_token = response.get("access_token")
    integration.refresh_token = response.get("refresh_token", integration.refresh_token)
    expires_in = response.get("expires_in")
    integration.expires_at = timezone.now() + timedelta(seconds=expires_in)
    integration.save()

    return integration.access_token


def linkedin_post(request):
    token = request.session.get("linkedin_token")
    if not token:
        return JsonResponse({"error": "Not authenticated"})

    # Get userinfo
    userinfo = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {token}"}
    ).json()
    sub_id = userinfo.get("sub")

    if not sub_id:
        return JsonResponse({"error": "Could not get LinkedIn user ID", "details": userinfo})

    # Post
    post_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    payload = {
        "author": f"urn:li:person:{sub_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": "Hello from Django with LinkedIn API! 🚀"},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    response = requests.post(post_url, headers=headers, json=payload)
    return JsonResponse(response.json())
import json
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta

from org.models import GoogleMeetIntegration
import requests
import requests
import json
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import redirect, get_object_or_404
from org.models import GoogleMeetIntegration
from ats.services.ats_services import refresh_google_token, build, Credentials
from google_auth_oauthlib.flow import Flow
try:
    from google_auth_oauthlib.flow import Flow  # optional; may not be available in some envs
except Exception:
    Flow = None
from google_auth_oauthlib.flow import Flow
def _ensure_flow():
    global Flow
    if Flow is None:
        try:
            from google_auth_oauthlib.flow import Flow as _Flow  # type: ignore
            Flow = _Flow
        except Exception:
            Flow = None
    return Flow


def google_login(request):
    tenant = request.user.tenant
    integration = get_object_or_404(GoogleMeetIntegration, tenant=tenant)

    FlowLocal = _ensure_flow()
    if not FlowLocal:
        return JsonResponse({"error": "google-auth-oauthlib is not installed"}, status=500)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": integration.CLIENT_ID,
                "client_secret": integration.CLIENT_SECRET,
                "redirect_uris": [integration.REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar.events"]
    )
    
    flow.redirect_uri = integration.REDIRECT_URI

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )
    return redirect(auth_url)

def refresh_google_tokenv2(integration: GoogleMeetIntegration):
    if integration.is_token_valid():
        return integration.access_token

    data = {
        "client_id": integration.CLIENT_ID,
        "client_secret": integration.CLIENT_SECRET,
        "refresh_token": integration.refresh_token,
        "grant_type": "refresh_token",
    }
    response = requests.post("https://oauth2.googleapis.com/token", data=data).json()

    integration.access_token = response.get("access_token")
    expires_in = response.get("expires_in")
    integration.expires_at = timezone.now() + timedelta(seconds=expires_in)
    integration.save()

    return integration.access_token

def oauth2callback(request):
    tenant = request.user.tenant
    integration = get_object_or_404(GoogleMeetIntegration, tenant=tenant)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": integration.CLIENT_ID,
                "client_secret": integration.CLIENT_SECRET,
                "redirect_uris": [integration.REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar.events"]
    )
    
    flow.redirect_uri = integration.REDIRECT_URI

    # ✅ pass redirect_uri via flow attribute to avoid duplicate kwarg error
    flow.fetch_token(
        authorization_response=request.build_absolute_uri()
    )
    creds = flow.credentials

    integration.access_token = creds.token
    integration.refresh_token = creds.refresh_token
    integration.expires_at = creds.expiry
    integration.save()

    return JsonResponse({
        "status": "authenticated",
        "tenant": tenant.id,
        "access_token": integration.access_token,
        "refresh_token": integration.refresh_token,
        "expires_at": integration.expires_at,
    })

import importlib
service_account = importlib.import_module("google.oauth2.service_account")
build = importlib.import_module("googleapiclient.discovery").build

# Safe/optional imports for Google libraries (some environments may not have them installed)
try:
    from googleapiclient.discovery import build
except Exception:
    try:
        import importlib
        build = importlib.import_module("googleapiclient.discovery").build
    except Exception:
        build = None

try:
    from google.oauth2.credentials import Credentials
except Exception:
    try:
        import importlib
        Credentials = importlib.import_module("google.oauth2.credentials").Credentials
    except Exception:
        Credentials = None

# Provide clear runtime errors when these helpers are used but missing
if build is None:
    def build(*args, **kwargs):
        raise RuntimeError("Missing dependency: google-api-python-client (googleapiclient); install it to use Google Calendar integration.")

if Credentials is None:
    class Credentials:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Missing dependency: google-auth (google.oauth2.credentials); install it to use Google Calendar integration.")

def create_google_meet_event(request, job_id):
    tenant = request.user.tenant
    integration = get_object_or_404(GoogleMeetIntegration, tenant=tenant)
    token = refresh_google_token(integration)

    creds = Credentials(token=token)
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": f"Interview for Job {job_id}",
        "start": {"dateTime": "2026-02-05T10:00:00+01:00", "timeZone": "Africa/Lagos"},
        "end": {"dateTime": "2026-02-05T11:00:00+01:00", "timeZone": "Africa/Lagos"},
        "conferenceData": {"createRequest": {"requestId": f"job-{job_id}-meet"}},
        "attendees": [{"email": "ayodelefestusng@gmail.com"}],
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1
    ).execute()

    meet_link = created_event.get("hangoutLink")
    return JsonResponse({"meet_link": meet_link})




class PostJobView(LoginRequiredMixin, CreateView):
    model = JobPosting
    form_class = JobPostingForm
    template_name = "ats/post_job.html"
    success_url = reverse_lazy("ats:manage_jobs")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.user.tenant
        return kwargs

    def form_valid(self, form):
        try:
            form.instance.tenant = self.request.user.tenant
            log_with_context(logging.INFO, "User is creating a new job posting", self.request.user)
            response = super().form_valid(form)
            
            # The object is now saved. self.object is the saved instance.
            job = self.object
            job.application_url = self.request.build_absolute_uri(
                reverse("ats:candidate_apply", kwargs={"job_id": job.pk})
            )
            job.save()
            with transaction.atomic():
                try:
                    job = JobPosting.objects.get(pk=job.pk, tenant=self.request.user.tenant)
                    # job = get_object_or_404(JobPosting, pk=pk, tenant=request.user.tenant)
                    job.status = "OPEN"
                    job.posted_at = timezone.now()
                    job.save()
                except Exception as e:
                    log_with_context(logging.ERROR, f"Failed to post job: {str(e)}", self.request.user)
                    return self.form_invalid(form)

                # Mock Integrations
                log_with_context(logging.INFO, f"Job {job.pk} publishing to external boards", self.request.user)
                linkedin_res = IntegrationService.post_job_to_linkedin(job,self.request.user)
                log_with_context(logging.INFO, f"Job {job.pk} published to LinkedIn", self.request.user)
                indeed_res = IntegrationService.post_job_to_indeed(job,self.request.user)
                log_with_context(logging.INFO, f"Job {job.pk} published to Indeed", self.request.user)

                log_with_context(logging.INFO, f"Job {job.pk} published to external boards", self.request.user)
                return JsonResponse({"status": "published", "integrations": {"linkedin": linkedin_res, "indeed": indeed_res}})
        
            
            # return response
        except Exception as e:
            log_with_context(logging.ERROR, f"Failed to post job: {str(e)}", self.request.user)
            return self.form_invalid(form)

@login_required
def get_relevant_locations(request):
    role_id = request.GET.get('role')
    tenant = request.user.tenant
    
    if role_id:
        selected_role = get_object_or_404(JobRole, id=role_id, tenant=tenant)
        locations = Location.objects.filter(
            org_units__roles__job_title=selected_role.job_title,
            tenant=tenant
        ).distinct()
        log_with_context(logging.INFO, f"Filtered locations for Role ID: {role_id}", request.user)
    else:
        locations = Location.objects.none()
        log_with_context(logging.ERROR, f"FALLBACK: Failed to generate locations for Role ID: {role_id}", request.user)
        
        

    # Return a simple partial template or just the form field
    return render(request, "partials/location_selector.html", {'locations': locations})
@login_required
def get_job_description(request):
    try:
        role_id = request.GET.get("role")
        log_with_context(logging.INFO, f"Filtered locations for Role ID: {role_id}", request.user)

        role = JobRole.objects.get(id=role_id, tenant=request.user.tenant)
        log_with_context(logging.INFO, f"Fetching description for role {role_id}", request.user)
        role = get_object_or_404(JobRole, id=role_id, tenant= request.user.tenant)
    
        # 1. Get locations for this specific JobTitle
        locations = Location.objects.filter(
            org_units__roles__job_title=role.job_title,
            tenant=request.user.tenant
        ).distinct()
        
        context = {
            "role": role,
            "locations": locations,
        }
        log_with_context(logging.INFO, f"Filtered locations for Role ID: {locations}", request.user)

        return render(request, "partials/role_info_snippet.html", context) 
        # return render(request, "partials/role_update_response.html", context)
    except Exception as e:
        return HttpResponse(b"Role details not found.", status=404)

@login_required
def get_locations_by_state(request):
    """HTMX view to return filtered locations based on selected state and optionally role."""
    state_id = request.GET.get('state')
    role_id = request.GET.get('role')
    tenant = request.user.tenant
    
    locations = Location.objects.filter(tenant=tenant)
    
    if state_id:
        locations = locations.filter(town__state_id=state_id)
    
    if role_id:
        try:
            selected_role = JobRole.objects.get(id=role_id, tenant=tenant)
            locations = locations.filter(org_units__roles__job_title=selected_role.job_title)
        except Exception:
            pass

    return render(request, "ats/partials/location_options.html", {'locations': locations.distinct()})


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
# --- HELPERS / HTMX SNIPPETS ---



@login_required
def generate_manager_share(request, job_id):
    job = get_object_or_404(JobPosting, id=job_id, tenant=request.user.tenant)
    share = JobShareLink.objects.create(
        job_posting=job,
        shared_by=request.user.employee,
        tenant=request.user.tenant
    )
    full_url = request.build_absolute_uri(reverse('ats:manager_view_share', kwargs={'share_id': share.id}))
    log_with_context(logging.INFO, f"Generated share link for Job {job_id}", request.user)
    return JsonResponse({'share_url': full_url})

class ManagerSharePortalView(View):
    def get(self, request, share_id):
        share = get_object_or_404(JobShareLink, id=share_id)
        return render(request, "ats/manager_view_share.html", {"share": share})


class ManageJobsView(LoginRequiredMixin, ListView):
    model = JobPosting
    template_name = "ats/manage_jobs.html"
    context_object_name = "jobs"

    def get_queryset(self):
        try:
            log_with_context(logging.INFO, "Accessing Job Management Board", self.request.user)
            return JobPosting.objects.filter(
                tenant=self.request.user.tenant,
                is_closed=False
            ).select_related('role__job_title').annotate(
                applicant_count=Count('applications')
            ).order_by('-created_at')
        except Exception as e:
            log_with_context(logging.ERROR, f"Error loading jobs: {e}", self.request.user)
            return JobPosting.objects.none()



class PublishJobView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            log_with_context(logging.INFO, f"Job {pk} publishing started", request.user)
            with transaction.atomic():
                job = get_object_or_404(JobPosting, pk=pk, tenant=request.user.tenant)
                job.status = "OPEN"
                job.posted_at = timezone.now()
                job.save()

                # Mock Integrations
                log_with_context(logging.INFO, f"Job {pk} publishing to external boards", request.user)
                linkedin_res = IntegrationService.post_job_to_linkedin(job,request.user)
                log_with_context(logging.INFO, f"Job {pk} published to LinkedIn", request.user)
                indeed_res = IntegrationService.post_job_to_indeed(job,request.user)
                log_with_context(logging.INFO, f"Job {pk} published to Indeed", request.user)

                log_with_context(logging.INFO, f"Job {pk} published to external boards", request.user)
                return JsonResponse({"status": "published", "integrations": {"linkedin": linkedin_res, "indeed": indeed_res}})
        
        except Exception as e:
            log_with_context(logging.ERROR, f"Publishing Failed: {e}", request.user)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)



# --- CANDIDATE & APPLICATION ---


class ManageCandidateView11(LoginRequiredMixin, ListView):
    model = Application
    template_name = "ats/manage_candidates.html"
    context_object_name = "applications"

    def get_queryset(self):
        log_with_context(logging.INFO, "Viewing candidate board", self.request.user)
        return Application.objects.filter(tenant=self.request.user.tenant
        ).select_related("candidate", "job_posting").order_by('-submitted_at')

class ManageCandidateView(LoginRequiredMixin, ListView):
    model = Application
    template_name = "ats/manage_candidates.html"
    context_object_name = "applications"

    def get_queryset(self):
        try:
            log_with_context(logging.INFO, "Loading candidate management board", self.request.user)
            return Application.objects.filter(tenant=self.request.user.tenant ).select_related("candidate", "job_posting")
        except Exception as e:
            log_with_context(logging.ERROR, f"Error in ManageCandidateView: {str(e)}",self.request.user,)
            return Application.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stages"] = [
            "APPLIED",
            "SCREENING",
            "SCHEDULED FOR INTERVIEW",
            "INTERVIEW",
            "OFFER",
            "HIRED",
            "REJECTED",
        ]
        return context

@login_required
@require_POST
def update_application_status(request, pk):
    """HTMX view to update application status and return the new status badge/indicator."""
    new_status = request.POST.get('status')
    tenant = request.user.tenant
    application = get_object_or_404(Application, pk=pk, tenant=tenant)
    
    if new_status:
        application.status = new_status
        application.save()
        log_with_context(logging.INFO, f"Updated Application {pk} status to {new_status}", request.user)
    
    return HttpResponse(f'<span class="badge badge-soft-primary animate-fade-in">{application.status}</span>'.encode())


@login_required
@require_POST
def reject_application(request, pk):
    """View to reject a candidate application."""
    tenant = request.user.tenant
    application = get_object_or_404(Application, pk=pk, tenant=tenant)
    
    application.status = "REJECTED"
    application.save()
    log_with_context(logging.INFO, f"Rejected Application {pk} for Candidate {application.candidate.name}", request.user)
    
    messages.success(request, f"Application from {application.candidate.name} has been rejected.")
    return redirect('ats:candidate_application', pk=pk)


# --- INTERVIEWS & SHARING ---

@login_required
def check_interview_conflict(request):
    """
    HTMX view to check for interview conflicts in real-time.
    """
    scheduled_at_str = request.POST.get('scheduled_at')
    interviewer_ids = request.POST.getlist('interviewers')
    tenant = request.user.tenant
    
    if not (scheduled_at_str and interviewer_ids):
        return HttpResponse("") # Not enough data yet

    try:
        from django.utils.dateparse import parse_datetime
        from datetime import timedelta
        
        scheduled_at = parse_datetime(scheduled_at_str)
        if not scheduled_at:
            return HttpResponse('<div class="alert alert-warning py-1 small mb-2">Invalid date format.</div>')
            
        # 1-hour conflict window
        start_window = scheduled_at - timedelta(minutes=59)
        end_window = scheduled_at + timedelta(minutes=59)
        
        conflicts = Interview.objects.filter(
            tenant=tenant,
            interviewers__id__in=interviewer_ids,
            scheduled_at__range=(start_window, end_window)
        ).distinct()
        
        if conflicts.exists():
            conflict_msg = "Conflict detected: "
            details = []
            for c in conflicts:
                # Find which specific interviewers are conflicting
                overlapping_interviewers = c.assigned_interviews.filter(id__in=interviewer_ids)
                names = ", ".join([f"{i.first_name} {i.last_name}" for i in overlapping_interviewers])
                details.append(f"{names} at {c.scheduled_at.strftime('%H:%M')}")
            
            return HttpResponse(f"""
                <div class="alert alert-danger py-2 small mb-3 animate-fade-in">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    <strong>{conflict_msg}</strong> {"; ".join(details)}
                </div>
            """)
        
        return HttpResponse("""
            <div class="alert alert-success py-2 small mb-3 animate-fade-in">
                <i class="bi bi-check-circle-fill me-2"></i>
                No schedule conflicts detected.
            </div>
        """)
        
    except Exception as e:
        log_with_context(logging.ERROR, f"Conflict Check Error: {e}", request.user)
        return HttpResponse("")

class ScheduleInterviewView(LoginRequiredMixin, DetailView):
    model = Application
    template_name = "ats/schedule_interview.html"
    context_object_name = "application"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = InterviewForm(
            tenant=self.request.user.tenant,
            initial={'application': self.object}
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = InterviewForm(request.POST, tenant=self.request.user.tenant)
        if form.is_valid():
            try:
                # Use the InterviewScheduler service
                interview = InterviewScheduler.schedule_interview(
                    application=self.object,
                    start_time=form.cleaned_data['scheduled_at'],
                    location=form.cleaned_data.get('location', 'In-Person'),
                    tenant=request.user.tenant,
                    interviewers=form.cleaned_data['interviewers']
                )
                
                if interview:
                    # Update setup_by
                    interview.setup_by = request.user.employee
                    interview.save()
                    
                    log_with_context(logging.INFO, f"Scheduled interview for App {self.object.id}", request.user)
                    
                    if interview.meeting_link:
                         messages.success(request, f"Interview Scheduled! Google Meet Link: {interview.meeting_link}")
                    else:
                         messages.success(request, "Interview Scheduled successfully!")
                    
                    return redirect('ats:manage_candidate')
                else:
                    messages.error(request, "Failed to schedule interview due to a system error.")
            except Exception as e:
                log_with_context(logging.ERROR, f"Scheduling Error: {e}", request.user)
                messages.error(request, f"Failed to schedule interview: {str(e)}")
        
        context = self.get_context_data(object=self.object)
        context['form'] = form
        return self.render_to_response(context)

# views.py
def get_schedule_modal(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    return render(request, "partials/schedule_modal_content.html", {
        'application': application,
        'candidate': application.candidate
    })
    
# views.py
def get_schedule_form(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    return render(request, "ats/partials/schedule_form_inner.html", {'application': application})

@login_required
@require_POST
def final_schedule(request, application_id):
    application = get_object_or_404(Application, id=application_id, tenant=request.user.tenant)
    
    start_time_str = request.POST.get('start_time')
    location = request.POST.get('location', 'Google Meet')
    
    if start_time_str:
        # Convert HTML5 datetime-local string to Python datetime
        start_time = parse_datetime(start_time_str)
        
        # Call our Scheduler Service
        success = InterviewScheduler.schedule_interview(
            application=application,
            start_time=start_time,
            location=location,
            tenant=request.user.tenant
        )
        
        if success:
            if request.headers.get('HX-Request'):
                return HttpResponse("""
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle me-2"></i> Interview Scheduled & Invite Sent!
                    </div>
                    <script>setTimeout(() => { window.location.reload(); }, 2000);</script>
                """)
            messages.success(request, "Interview successfully scheduled.")
        else:
            return HttpResponse('<div class="alert alert-danger">Failed to sync with calendar.</div>')
            
    return redirect('ats:manage_jobs')

# --- CANDIDATE & APPLICATION ---

class CandidateApplyView(CreateView):
    model = Candidate
    form_class = CandidateApplicationForm
    template_name = "ats/candidate_apply_form.html"

    def form_valid(self, form):
        job_id = self.kwargs.get("job_id")
        job_posting = get_object_or_404(JobPosting, id=job_id)

        try:
            with transaction.atomic():
                candidate = form.save(commit=False)
                candidate.tenant = job_posting.tenant  
                candidate.save()

                application = Application.objects.create(
                    candidate=candidate,
                    job_posting=job_posting,
                    tenant=job_posting.tenant,
                    status="APPLIED",
                )

                # Auto-populate requirements
                role_skills = job_posting.role.skills.all()
                for rs in role_skills:
                    CandidateSkillProfile.objects.get_or_create(
                        candidate=candidate,
                        skill=rs.skill_name,
                        tenant=job_posting.tenant,
                        defaults={"level": 1},
                    )

            # AI Processing if enabled
            if job_posting.ai_enabled and candidate.resume:
                try:
                    from .ai_service import ATSAIService, ResumeValidationError
                    
                    # Validate resume file
                    ATSAIService.validate_resume_file(candidate.resume)
                    
                    # Extract resume data using AI
                    log_with_context(logging.INFO, "Starting AI resume analysis", request.user or "anonymous")
                    resume_data = ATSAIService.extract_resume_data(candidate.resume)
                    
                    # Analyze application fit
                    analysis_results = ATSAIService.analyze_application_fit(resume_data, job_posting)
                    
                    # Generate AI comments
                    ai_comments = ATSAIService.generate_ai_comments(resume_data, job_posting, analysis_results)
                    
                    # Store AI comments in application
                    application.ai_comments = ai_comments
                    application.save()
                    
                    log_with_context(
                        logging.INFO, 
                        f"AI analysis completed for application {application.id} - Fit Score: {analysis_results.get('overall_fit_score', 0)}/100",
                        request.user or "anonymous"
                    )
                    messages.info(
                        request, 
                        f"✓ AI analysis complete: {analysis_results.get('overall_fit_score', 0)}% job fit"
                    )
                    
                except ResumeValidationError as ve:
                    log_with_context(logging.WARNING, f"Resume validation failed: {str(ve)}", request.user or "anonymous")
                    messages.warning(request, f"Resume validation: {str(ve)}")
                except Exception as ai_error:
                    log_with_context(logging.ERROR, f"AI processing error: {str(ai_error)}", request.user or "anonymous")
                    messages.warning(request, "AI analysis could not be completed, but your application was submitted.")

            # Trigger async resume processing after candidate is saved
            transaction.on_commit(lambda c=candidate: process_resume_async.delay(c.id))

            # ASYNCHRONOUS TRIGGER: Process resume in background thread 
            # (In production, use Celery: ResumeParserService.process_candidate_resume.delay(candidate.id))
            threading.Thread(target=ResumeParserService.process_candidate_resume, args=(candidate.id,)).start()
            
            log_with_context(logging.INFO, f"New application for Job {job_id}", f"Candidate:{candidate.email}")
            return redirect("ats:application_success")

        except DatabaseError as e:
            log_with_context(logging.ERROR, f"Application DB Error: {e}", "System")
            return HttpResponse("A database error occurred. Please try again later.", status=500)

class ViewCandidateProfileView(LoginRequiredMixin, DetailView):
    model = Candidate
    template_name = "ats/candidate_profile.html"
    context_object_name = "candidate"

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            candidate = self.get_object()
            log_with_context(logging.INFO, f"Viewing profile for Candidate {candidate.id}", self.request.user)

            # Spider Chart Logic
            competencies = candidate.competency_profiles.all()
            context["spider_labels"] = json.dumps([cp.competency.name for cp in competencies])
            context["spider_values"] = json.dumps([cp.level for cp in competencies])
            return context
        except Exception as e:
            log_with_context(logging.ERROR, f"Error loading candidate profile: {e}", self.request.user)
            return {}


# --- ANALYTICS & DASHBOARD ---

class JobAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "ats/job_analytics.html"

    def get_context_data(self, **kwargs):
        try:
            log_with_context(logging.INFO, "Generating Analytics Dashboard", self.request.user)
            context = super().get_context_data(**kwargs)
            tenant = self.request.user.tenant

            # Applications Chart
            six_months_ago = timezone.now() - datetime.timedelta(days=180)
            apps = Application.objects.filter(tenant=tenant, submitted_at__gte=six_months_ago) \
                   .annotate(month=TruncMonth("submitted_at")) \
                   .values("month").annotate(count=Count("id")).order_by("month")

            context["chart_apps_labels"] = json.dumps([x["month"].strftime("%b") for x in apps])
            context["chart_apps_data"] = json.dumps([x["count"] for x in apps])
            
            context["total_candidates"] = Application.objects.filter(tenant=tenant).count()
            return context
        except Exception as e:
            log_with_context(logging.ERROR, f"Analytics generation failed: {e}", self.request.user)
            return {"error": "Could not load analytics."}



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
    def get_context_data(self, **kwargs):
        # Add extra context for the template
        context = super().get_context_data(**kwargs)
        application = context["application"]

        # Example: include candidate and job posting details
        context["candidate"] = application.candidate
        context["job_posting"] = application.job_posting

        # Example: include a flag for whether the user can edit
        context["can_edit"] = self.request.user.has_perm("ats.change_application")

        return context

class JobLeaderboardView(LoginRequiredMixin, DetailView):
    model = JobPosting
    template_name = "ats/job_leaderboard.html"
    context_object_name = "job"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["leaderboard"] = RankingService.get_ranked_candidates(self.object)
        return context

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



class CandidateCommunicationView(LoginRequiredMixin, TemplateView):
    template_name = "ats/candidate_communication.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["applications"] = Application.objects.filter(
            tenant=self.request.user.tenant
        )
        return context

    
class NotifyCandidateView(LoginRequiredMixin, View):
        def post(self, request, pk):
            application = get_object_or_404(Application, pk=pk, tenant=request.user.tenant)
            log_with_context(
                logging.INFO,
                f"Notifying Candidate ID: {application.candidate_id} for Job: {application.job_posting.title}",
                request.user,
            )
            return JsonResponse({"status": "success"})  