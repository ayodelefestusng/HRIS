from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from ats.views import linkedin_login, linkedin_callback, linkedin_post, google_login, refresh_google_token,oauth2callback, create_google_meet_event
from ats.services.ats_services import refresh_google_token

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Core apps
    path("", include("hr.urls")),
    path("employees/", include("employees.urls")),
    path("users/", include("users.urls")),
    # Authentication (ONLY ONCE)
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("allauth.urls")),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Notifications
    path("api/notifications/", include("notifications.urls")),
    # Existing Modules (HTML + API hybrid)
    path("org/", include("org.urls")),
    path("workflow/", include("workflow.urls")),
    path("payroll/", include("payroll.urls")),
    path("leave/", include("leave.urls")),
    path("ats/", include("ats.urls")),
    path("onboarding/", include("onboarding.urls")),
    path("rbac/", include("rbac.urls")),
    path("analytics/", include("analytics.urls")),
    # New Modules
    path("development/", include("development.urls")),
    path("discipline/", include("discipline.urls")),
    path("engagement/", include("engagement.urls")),
    path("attendance/", include("attendance.urls")),
    path("benefits/", include("benefits.urls")),
    path("performance/", include("performance.urls")),
    path("core/", include(("core.urls", "core"), namespace="core")),
]
urlpatterns += [ path("linkedin/login/", linkedin_login, name="linkedin_login"),
                path("linkedin/callback/", linkedin_callback, name="linkedin_callback"),
                path("linkedin/post/", linkedin_post, name="linkedin_post"), ]

urlpatterns += [ 
    # path("googlemeet/login/", google_login, name="googlemeet_login"),
path("google/login/", google_login, name="google_login"),

# Google OAuth callback (Google redirects back here with ?code=...) 
path("oauth2callback/", oauth2callback, name="oauth2callback"),

# Example endpoint to create a Google Meet event after authentication 
path("google/create-meet/<int:job_id>/", create_google_meet_event, name="create_google_meet_event"),
path("google/refresh/", refresh_google_token, name="google_refresh"),



    path('tinymce/', include('tinymce.urls')),
 ]


# Static & Media (development only)
import os

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
  
