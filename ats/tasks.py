from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import logging
from ats.models import Application, Offer, Candidate
from workflow.services.workflow_service import ResumeParserService
from ats.models import OnboardingPlan, OnboardingTask

from org.models import RoleSkillRequirement, RoleCompetencyRequirement
from django.db.models import Count, Avg, F, Q, ExpressionWrapper, FloatField
logger = logging.getLogger(__name__)


@shared_task
def auto_close_old_applications():
    count = Application.objects.filter(status="NEW").count()
    # Logic to close them could go here
    return f"Checked {count} new applications"


@shared_task
def remind_pending_onboarding_tasks():
    count = 0
    for plan in OnboardingPlan.objects.filter(completed_at__isnull=True):
        pending = plan.tasks.filter(status="PENDING")
        if pending.exists():
            count += 1
            # You can send reminders here
    return f"Checked {count} onboarding plans"


@shared_task
def send_automated_offer_email(offer_id):
    """
    Triggered when an Offer is created. Sends the letter to the candidate.
    """
    try:
        offer = Offer.objects.select_related(
            "application__candidate", "application__tenant"
        ).get(id=offer_id)
        candidate = offer.application.candidate

        subject = (
            f"Job Offer: {offer.application.job_posting.title} at {offer.tenant.name}"
        )
        message = f"Hello {candidate.full_name},\n\nWe are pleased to offer you the position. Please find your offer letter attached."

        # In a real setup, you'd attach the offer.offer_letter.path here
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [candidate.email])

        logger.info(f"[CELERY_OFFER_SENT] Offer {offer_id} sent to {candidate.email}")
        return f"Offer sent to {candidate.email}"
    except Offer.DoesNotExist:
        return "Offer not found"


@shared_task
def nag_pending_onboarding_requirements():
    """
    Daily task: Find mandatory tasks past their due date and alert the employee.
    """
    today = timezone.now().date()
    overdue_tasks = OnboardingTask.objects.filter(
        is_completed=False, due_date__lt=today, requirement__is_mandatory=True
    ).select_related("employee", "plan__tenant")

    count = 0
    for task in overdue_tasks:
        # Trigger Notification (Email/Push)
        logger.warning(
            f"[ONBOARDING_OVERDUE] Tenant: {task.plan.tenant.code} | "
            f"Employee: {task.employee.full_name} | Task: {task.title}"
        )
        count += 1

    return f"Processed {count} overdue onboarding tasks"


@shared_task(bind=True, max_retries=3)
def process_resume_async(self, candidate_id):
    try:
        ResumeParserService.process_candidate_resume(candidate_id)
        return f"Success: Processed Candidate {candidate_id}"
    except Exception as exc:
        logger.error(f"Error processing resume for {candidate_id}: {exc}")
        # Retry the task if it fails (e.g., temporary file access issue)
        raise self.retry(exc=exc, countdown=60)

def get_detailed_scorecard(candidate, job_posting):
    return candidate.get_detailed_scorecard(job_posting)


class AutoMatchService:
    @staticmethod
    def get_best_matches(job_posting, limit=5):
        """
        Calculates a 'Fit Score' based on:
        1. Number of matching skills (weighted 70%)
        2. Average level of matching skills (weighted 30%)
        """
        # Get the IDs of skills required for this job (assuming JobPosting has a skills relation)
        # For now, we'll pull from the JobRole's typical requirements
        required_skill_ids = job_posting.role.competencies.values_list('id', flat=True)
        
        candidates = Candidate.objects.filter(
            tenant=job_posting.tenant,
            skill_profiles__skill_id__in=required_skill_ids
        ).annotate(
            # Count how many of the job's required skills the candidate has
            match_count=Count('skill_profiles', filter=Q(skill_profiles__skill_id__in=required_skill_ids)),
            # Calculate the average level of those matching skills
            avg_level=Avg('skill_profiles__level', filter=Q(skill_profiles__skill_id__in=required_skill_ids))
        ).annotate(
            # Final Fit Score calculation (Normalized to 100)
            fit_score=ExpressionWrapper(
                ((F('match_count') / len(required_skill_ids)) * 70) + (F('avg_level') * 6),
                output_field=FloatField()
            )
        ).order_by('-fit_score')

        return candidates[:limit]