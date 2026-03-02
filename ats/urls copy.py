from django.urls import path
from django.views.generic import TemplateView
from .views import (
    PostJobView,
    PublishJobView,
    JobAnalyticsView,
    # ParseResumeView,
    # ExtractResumeInfoView,
    ManageCandidateView,
    ViewCandidateProfileView,
    ViewCandidateApplicationView,
    SearchCandidateView,
    CandidateCommunicationView,
    ScheduleInterviewView,
    NotifyCandidateView,
    job_preview_modal,get_job_description,JobBoardDetailPreview,CandidateApplyView,
    AnonymizeCandidateView,
    JobLeaderboardView,ManageJobsView,generate_manager_share,get_relevant_locations,
    get_locations_by_state,update_application_status,
    final_schedule,get_schedule_modal,get_schedule_form,ManagerSharePortalView,
    check_interview_conflict,linkedin_login,linkedin_post,linkedin_callback
)

app_name = "ats"

urlpatterns = [
    # HTMX
    path( "get-description/",get_job_description,name="get_job_description",),
    path("generate-share/<int:job_id>/", generate_manager_share, name="generate_share"),
    path("job_preview_modal/",job_preview_modal,name="job_preview",),
    path(
        "get-locations-by-state/", 
        get_locations_by_state, 
        name="get_locations_by_state"
    ),
    path(
        "get-relevant-locations/", 
        get_relevant_locations, 
        name="get_relevant_locations"
    ),


  # Job Posting
    path("job/post/", PostJobView.as_view(), name="post_job"),
    path("manage-jobs/", ManageJobsView.as_view(), name="manage_jobs"),
    path("job/post/<int:pk>/publish/", PublishJobView.as_view(), name="publish_job"),
    # path("job-leaderboard/<int:pk>/", JobLeaderboardView.as_view(), name="job_leaderboard"),

# Candidate Management
    path("candidate/manage/", ManageCandidateView.as_view(), name="manage_candidate"),
    path("candidate/manage/<int:pk>/update-status/", update_application_status, name="update_application_status"),
    path("candidate/manage/<int:pk>/anonymize/", AnonymizeCandidateView.as_view(), name="anonymize_candidate"),

# Interview Scheduling
    path("interview/schedule/<int:pk>/",ScheduleInterviewView.as_view(),name="schedule_interview",),
    path("interview/check-conflict/", check_interview_conflict, name="check_interview_conflict"),
    path("apply/<int:job_id>/",CandidateApplyView.as_view(),name="candidate_apply",),
    path("candidate/manage/<int:pk>/profile/",ViewCandidateProfileView.as_view(),name="candidate_profile",),
    path("schedule-interview/final/<int:application_id>/", final_schedule, name="final_schedule"),
    path("manager-share/<int:job_id>/", ManagerSharePortalView.as_view(), name="manager_share_portal"),
    # urls.py
    path("get-schedule-modal/<int:application_id>/", get_schedule_modal, name="get_schedule_modal"),
    path("get-schedule-form/<int:application_id>/", get_schedule_form, name="get_schedule_form"),
    path("schedule-interview/final/<int:application_id>/", final_schedule, name="final_schedule"),
    
  # --- ANALYTICS & DASHBOARD ---
    path("job/analytics/", JobAnalyticsView.as_view(), name="job_analytics"),
    path("candidate/search/", SearchCandidateView.as_view(), name="search_candidates"),
    path("candidate/manage/<int:pk>/application/",ViewCandidateApplicationView.as_view(),name="candidate_application",),
    path("job-leaderboard/<int:pk>/", JobLeaderboardView.as_view(), name="job_leaderboard"),
    path("job-preview/<int:pk>/", JobBoardDetailPreview.as_view(), name="job_preview_public"),
    path("candidate/communication/",CandidateCommunicationView.as_view(),name="candidate_communication",),
    path("interview/schedule/<int:pk>/notify/",NotifyCandidateView.as_view(),name="notify_candidate",),
    path('apply/success/', TemplateView.as_view(template_name="ats/application_success.html"), name='application_success'),


path("linkedin/login/", linkedin_login, name="linkedin_login"),
path("linkedin/callback/", linkedin_callback, name="linkedin_callback"),
path("linkedin/post/", linkedin_post, name="linkedin_post"),


]

 # Resume Parsing
    # path("resume/parse/", ParseResumeView.as_view(), name="parse_resume"),
    # path(
    #     "resume/parse/<int:pk>/extract/",
    #     ExtractResumeInfoView.as_view(),
    #     name="extract_resume_info",
    # ),
    
  # urls.py
# path(
#     "job-preview/<int:id>/", # DetailView uses 'pk' by default
#     JobBoardDetailPreview.as_view(),
#     name="job_preview_public",
# ),
