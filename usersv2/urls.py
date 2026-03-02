from django.urls import path

from . import views
from .views import *

app_name = 'users' 


urlpatterns = [
        # path("",home, name="home"),
   path("about", about, name="about"),
  path("contact", contact, name="contact"),

    #Account Management 
     path("check-username/", views.check_username, name='check-username'),

     path("register/", register, name="register"),
    path("setup-password/<int:user_id>/<str:token>/", setup_password, name="setup_password"),
    path("password-reset/", password_reset_request, name="password_reset"),
    path("change-password/", change_password, name="change_password"),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
#   path('verify_mfa/<str:email>/', verify_mfa, name='verify_mfa'),
  path('verify_mfa/', verify_mfa, name='verify_mfa'),

  path('reset_qr/', reset_qr, name='reset_qr'),
    # path('disable-2fa/', disable_2fa, name='disable_2fa'),

    
        path('terms-and-privacy/', views.terms_and_privacy, name='terms_and_privacy'),

    path('solutions-overview/', solutions_overview, name='solutions_overview'),
    path('solutions/<slug:slug>/', solution_detail, name='solution_detail'),
    path('platform/', platform_view, name='platform'),
    path('industries/', industries, name='industries'),

    path('industries/<slug:industry_slug>/', industry_detail, name='industry_detail'),
    path('case-studies/', case_studies, name='case_studies'),
    path('case-studies/<slug:slug>/', case_study_detail, name='case_study_detail'),
    path('blog/', blog_list, name='blog_list'),
    path('blog/<slug:slug>/', blog_detail, name='blog_detail'),
    path('demo-booking/', demo_booking, name='demo_booking'),
    path('thank-you/', thank_you, name='thank_you'),
    path('', HomeView.as_view(), name='home'),

    path('', views.DemoBookingView.as_view(), name='demo_booking'),
    path('success/', views.DemoSuccessView.as_view(), name='demo_success'),
    path('partial/', views.DemoBookingPartialView.as_view(), name='demo_booking_partial'),
    path('calendly-webhook/', views.CalendlyWebhookView.as_view(), name='calendly_webhook'),

]

hmtx_views = [
    path("check_username/", views.check_username, name='check_username'),
 

]

urlpatterns += hmtx_views


