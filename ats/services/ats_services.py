from workflow.services.workflow_service import create_notification
import hashlib
from ats.models import Application, Interview, Offer, Candidate
from employees.models import Employee
from django.db import transaction
import logging
from django.db.models import Count, Q, F, ExpressionWrapper, FloatField
from django.db import transaction
from ats.models import Candidate
from django.db.models import Avg 
from django.utils import timezone
from ats.models import (
    OnboardingPlan,
    OnboardingTask,
    OnboardingTaskTemplate,
)
import logging

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

import pdfplumber
import logging
import re
from ats.models import Candidate, CandidateSkillProfile
from org.views import log_with_context

from org.models import GoogleMeetIntegration
from datetime import timedelta
from google_auth_oauthlib.flow import Flow

# Safe/optional imports for Google libraries
try:
    from googleapiclient.discovery import build
except Exception:
    build = None

try:
    from google.oauth2.credentials import Credentials
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

import requests
from django.conf import settings

def refresh_google_token(integration: GoogleMeetIntegration):
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
    if expires_in:
        integration.expires_at = timezone.now() + timedelta(seconds=expires_in)
    integration.save()

    return integration.access_token

class ResumeParserService:
    @staticmethod
    def extract_text_from_pdf(pdf_file):

        text = ""
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + " "
            return text.lower()
        except Exception as e:
            logger.error(f"PDF Extraction Error: {e}")
            return ""

    @staticmethod
    def calculate_skill_level(text, skill_name):
        skill_name = skill_name.lower()
        pattern = rf"{re.escape(skill_name)}.*?(\d+)\s*(?:years|yrs|year)"
        match = re.search(pattern, text)
        if match:
            years = int(match.group(1))
            if years >= 7:
                return 5
            if years >= 5:
                return 4
            if years >= 3:
                return 3
            return 2
        return 1

    @classmethod
    def process_candidate_resume(cls, candidate_id):
        """Asynchronous-friendly method to process resume."""
        try:
            candidate = Candidate.objects.get(id=candidate_id)
            if not candidate.resume:
                return

            resume_text = cls.extract_text_from_pdf(candidate.resume)
            profiles = CandidateSkillProfile.objects.filter(candidate=candidate)

            for profile in profiles:
                skill_name = profile.skill.name
                if skill_name.lower() in resume_text:
                    profile.level = cls.calculate_skill_level(resume_text, skill_name)
                    profile.save()

            log_with_context(
                logging.INFO, f"Resume parsed for candidate {candidate_id}", "System"
            )
        except Exception as e:
            logger.error(f"Background Parsing Failed for Candidate {candidate_id}: {e}")



class IntegrationService:
    @staticmethod
    def post_job_to_linkedin(job_posting, user=None):
        """
        Integration to post a job to LinkedIn using OAuth2.
        Requires a valid access token stored in session or settings.
        """
        try:
            token = getattr(settings, "LINKEDIN_ACCESS_TOKEN", None)
            if not token:
                raise Exception("No LinkedIn access token configured")

            # Get userinfo to extract LinkedIn ID
            userinfo = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            ).json()
            sub_id = userinfo.get("sub")
            if not sub_id:
                raise Exception(f"Could not get LinkedIn user ID: {userinfo}")

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
                        "shareCommentary": {
                            "text": f"New job posted: {job_posting.title}\nApply here: {job_posting.get_absolute_url()}"
                        },
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }

            response = requests.post(post_url, headers=headers, json=payload)
            data = response.json()

            if response.status_code != 201 and response.status_code != 200:
                raise Exception(f"LinkedIn API error: {data}")

            external_id = data.get("id", f"li-{job_posting.pk}-api")
            url = f"https://www.linkedin.com/feed/update/{external_id}"

            log_with_context(logging.INFO, f"Job {job_posting.pk} posted to LinkedIn", user)

            return {
                "status": "success",
                "platform": "LinkedIn",
                "external_id": external_id,
                "url": url,
            }

        except Exception as e:
            log_with_context(logging.ERROR, f"LinkedIn posting failed: {e}", user)
            return {"status": "error", "platform": "LinkedIn", "message": str(e)}

    @staticmethod
    def post_job_to_indeed(job_posting, user=None):
        """
        Mock integration to post a job to Indeed.
        """
        try:
            return {
                "status": "success",
                "platform": "Indeed",
                "external_id": f"ind-{job_posting.pk}-mock",
                "url": f"https://www.indeed.com/viewjob?jk=mock-{job_posting.pk}",
            }
        except Exception as e:
            log_with_context(logging.ERROR, f"Indeed posting failed: {e}", user)
            return {"status": "error", "platform": "Indeed", "message": str(e)}



class IntegrationServicev2:
    @staticmethod
    def post_job_to_linkedin(job_posting):
        """
        Mock integration to post a job to LinkedIn.
        In a real scenario, this would use LinkedIn's API with OAuth2.
        """
        # Simulate API call latency
        # time.sleep(1)
        return {
            "status": "success",
            "platform": "LinkedIn",
            "external_id": f"li-{job_posting.pk}-mock",
            "url": f"https://www.linkedin.com/jobs/view/mock-{job_posting.pk}",
        }

    @staticmethod
    def post_job_to_indeed(job_posting):
        """
        Mock integration to post a job to Indeed.
        """
        # time.sleep(0.5)
        return {
            "status": "success",
            "platform": "Indeed",
            "external_id": f"ind-{job_posting.pk}-mock",
            "url": f"https://www.indeed.com/viewjob?jk=mock-{job_posting.pk}",
        }


def move_application_to_stage(application, stage):
    application.status = stage
    application.save()

    # ✅ Notify hiring manager
    posting = application.job_posting
    hiring_manager = getattr(posting, "hiring_manager", None)

    if hiring_manager:
        create_notification(
            recipient=hiring_manager.user,
            title="Candidate Moved to Next Stage",
            message=(
                f"{application.applicant.full_name} has moved to the {stage} stage "
                f"for {posting.title}."
            ),
            target=application,
            send_email=True,
        )

    return application


def schedule_interview(application, interviewer, scheduled_at):
    interview = Interview.objects.create(
        application=application,
        interviewer=interviewer,
        scheduled_at=scheduled_at,
    )

    # Notify interviewer
    create_notification(
        recipient=interviewer.user,
        title="New Interview Scheduled",
        message=f"You have an interview scheduled for {application.applicant.full_name}.",
        target=interview,
        send_email=True,
    )

    return interview


def create_offer(application, salary, start_date):
    offer = Offer.objects.create(
        application=application,
        salary=salary,
        start_date=start_date,
    )

    move_application_to_stage(application, "OFFER")

    return offer


class HiringService:
    @staticmethod
    @transaction.atomic
    def convert_candidate_to_employee(application_id):
        """
        Transitions a candidate to the employee table and initializes their onboarding.
        """
        try:
            app = Application.objects.select_related(
                "candidate", "job_posting", "tenant"
            ).get(application_id=application_id)

            # 1. Create Employee Profile
            employee = Employee.objects.create(
                tenant=app.tenant,
                first_name=app.candidate.full_name.split()[0],
                last_name=" ".join(app.candidate.full_name.split()[1:]),
                email=app.candidate.email,
                phone_number=app.candidate.phone,
                job_role=app.job_posting.job_role,
                status="ONBOARDING",
            )

            # 2. Link Employee to Onboarding Plan
            if hasattr(app, "onboarding_plan"):
                plan = app.onboarding_plan
                plan.employee = employee
                plan.status = "leave_application"  # Moving to Orientation Phase
                plan.save()

            # 3. Log the transition for security audit
            logger.info(
                f"[HIRE_SUCCESS] Tenant: {app.tenant.code} | "
                f"Candidate {app.candidate.full_name} converted to Employee ID: {employee.id} | "
                f"Post: {app.job_posting.title}"
            )

            return employee
        except Exception as e:
            logger.error(f"Error converting candidate to employee: {e}", exc_info=True)
            raise



def create_onboarding_plan(employee, template, start_date=None):
    plan = OnboardingPlan.objects.create(
        employee=employee,
        template=template,
        start_date=start_date or timezone.now().date(),
    )

    task_templates = template.task_templates.order_by("order")

    for t in task_templates:
        task = OnboardingTask.objects.create(
            plan=plan,
            title=t.title,
            description=t.description,
            order=t.order,
        )

        create_notification(
            recipient=employee.user,
            title="New Onboarding Task Assigned",
            message=f"You have a new onboarding task: {task.title}",
            target=task,
            send_email=False,
        )

    create_notification(
        recipient=employee.user,
        title="Welcome to the Company!",
        message="Your onboarding plan has been created.",
        target=plan,
        send_email=True,
    )

    return plan


def complete_task(task: OnboardingTask):
    task.status = "DONE"
    task.completed_at = timezone.now()
    task.save()

    create_notification(
        recipient=task.plan.employee.user,
        title="Onboarding Task Completed",
        message=f"You completed: {task.title}",
        target=task,
        send_email=False,
    )

    if not task.plan.tasks.exclude(status="DONE").exists():
        task.plan.completed_at = timezone.now()
        task.plan.save()

        create_notification(
            recipient=task.plan.employee.user,
            title="Onboarding Completed",
            message="Congratulations! You have completed your onboarding.",
            target=task.plan,
            send_email=True,
        )

    return task


def update_onboarding_progress(plan_id):
    plan = OnboardingPlan.objects.get(id=plan_id)

    # Logic: If all DOCUMENT types are verified, move to Orientation
    mandatory_docs_pending = plan.tasks.filter(
        requirement__req_type="DOCUMENT", verified_at__isnull=True
    ).exists()

    if not mandatory_docs_pending and plan.status == "IN_PROGRESS":
        plan.status = "leave_application"  # Trigger Orientation View

    # Recalculate percentage based on VERIFIED tasks for Admin precision
    total = plan.tasks.count()
    verified = plan.tasks.filter(verified_at__isnull=True).count()
    plan.progress = (verified / total) * 100

    plan.save()
    return plan


class PrivacyService:
    @staticmethod
    @transaction.atomic
    def anonymize_candidate(candidate_id, tenant):
        """
        Wipes PII from a candidate while preserving non-identifying data for HR metrics.
        """
        try:
            candidate = Candidate.objects.select_for_update().get(id=candidate_id, tenant=tenant)
            
            # 1. Generate a unique hash for the email so we don't allow 
            # the same person to re-apply immediately if that's a policy,
            # but we can't see the original email.
            email_hash = hashlib.sha256(candidate.email.lower().encode()).hexdigest()[:12]
            
            # 2. Wipe Personal Identifiable Information (PII)
            candidate.full_name = f"Anonymized_User_{email_hash}"
            candidate.email = f"deleted_{email_hash}@anonymized.com"
            candidate.phone = "00000000000"
            candidate.notes = "Content deleted for privacy compliance."
            
            # 3. Handle Files (Delete the physical resume)
            if candidate.resume:
                candidate.resume.delete(save=False)
                candidate.resume = None
            
            # 4. Update status flags
            candidate.is_anonymized = True
            candidate.anonymized_at = timezone.now()
            
            candidate.save()
            
            # Note: We do NOT delete skill_profiles or competency_profiles.
            # This allows the tenant to still see "We have 50 candidates with Python skills"
            # without knowing WHO they are.
            
            return True, "Candidate successfully anonymized."
        except Candidate.DoesNotExist:
            return False, "Candidate not found."
        
        

class RankingService:
    @staticmethod
    def get_ranked_candidates(job_posting, limit=10):
        """
        Calculates scores for all applicants of a job and returns the top N.
        """
        applications = job_posting.applications.select_related('candidate').prefetch_related(
            'candidate__experience', 'candidate__education', 
            'candidate__skill_profiles', 'candidate__competency_profiles'
        )
        
        ranked_list = []
        for app in applications:
            # Reusing our detailed scorecard logic
            score_data = app.candidate.get_detailed_scorecard(job_posting)
            ranked_list.append({
                'application': app,
                'candidate': app.candidate,
                'score': score_data['total_score'],
                'meets_min_exp': score_data['meets_min_exp'],
                'skill_match_pct': score_data['skill_match_percent'] 
            })
            
        # Sort by total score descending
        ranked_list.sort(key=lambda x: x['score'], reverse=True)
        return ranked_list[:limit]
    
class InterviewScheduler:
    @staticmethod
    def schedule_interview(application, start_time, location, tenant, interviewers=None):
        try:
            # Format time for Google/Outlook API (yyyymmddTHHMM)
            formatted_time = start_time.strftime("%Y%m%dT%H%M")
            
            interview = Interview.objects.create(
                application=application,
                scheduled_at=start_time,
                location=location,
                tenant=tenant
            )
            
            if location == "Google Meet":
                link = InterviewScheduler.generate_meet_link(interview)
                if link:
                    interview.meeting_link = link
                    interview.save()
            
            if interviewers:
                interview.interviewers.set(interviewers)

            # Update Application Status
            application.status = "SCHEDULED FOR INTERVIEW"
            application.save()

            # Send Email Invite
            InterviewScheduler.send_invite_email(interview)
            
            return interview
        except Exception as e:
            logging.error(f"Scheduling Error: {e}")
            return None
    
    @staticmethod
    def send_invite_email(interview):
        """Sends an email invitation to the candidate."""
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            candidate = interview.application.candidate
            job_title = interview.application.job_posting.role.job_title.name
            
            subject = f"Interview Invitation: {job_title} at {interview.tenant.name}"
            
            message = f"""Dear {candidate.full_name},

We are pleased to invite you to an interview for the position of {job_title}.

Date & Time: {interview.scheduled_at.strftime('%B %d, %Y at %I:%M %p')}
Location: {interview.location}
"""
            if interview.meeting_link:
                message += f"\nJoin via Google Meet: {interview.meeting_link}\n"
            
            message += f"\n\nBest regards,\n{interview.tenant.name} Recruitment Team"
            
            send_mail(
                subject, 
                message, 
                settings.DEFAULT_FROM_EMAIL, 
                [candidate.email],
                fail_silently=True
            )
            logger.info(f"Interview invite sent to {candidate.email}")
        except Exception as e:
            logger.error(f"Failed to send interview email: {e}")

    @staticmethod
    def generate_meet_link(interview):
        """
        Generates a Google Meet link using the Calendar API.
        Adopts the GoogleMeetIntegration model for tenant-specific auth.
        """
        try:
            from org.models import GoogleMeetIntegration
            
            tenant = interview.tenant
            integration = GoogleMeetIntegration.objects.filter(tenant=tenant).first()
            
            if not integration:
                logger.warning(f"GoogleMeetIntegration not configured for tenant {tenant}")
                return None

            token = refresh_google_token(integration)
            creds = Credentials(token=token)
            service = build('calendar', 'v3', credentials=creds)

            start_time = interview.scheduled_at.isoformat()
            end_time = (interview.scheduled_at + timedelta(hours=1)).isoformat()

            event = {
                'summary': f"Interview: {interview.application.candidate.full_name}",
                'location': 'Google Meet',
                'description': f"Interview for {interview.application.job_posting.role.job_title.name}",
                'start': {'dateTime': start_time, 'timeZone': 'Africa/Lagos'},
                'end': {'dateTime': end_time, 'timeZone': 'Africa/Lagos'},
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"interview-{interview.id}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                },
                'attendees': [
                    {'email': interview.application.candidate.email},
                    # Add interviewers if needed
                ],
            }

            created_event = service.events().insert(
                calendarId='primary', 
                body=event, 
                conferenceDataVersion=1
            ).execute()

            # Return the hangoutLink directly (simpler and more reliable)
            return created_event.get('hangoutLink')

        except Exception as e:
            logger.error(f"Failed to generate Meet link: {e}")
            return None
      