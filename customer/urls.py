from django.urls import path
from .views import (
    CRMPipelineView,OnboardTenantView,TenantDetailView,ChatView,
    PasswordSuccessView, SetPasswordView,LoanApplicationView,LoanConfirmedView, BankingLoginView, BankingLockedView, BankingForgotPasswordView, BankingVerifyOTPView, update_biller_items,
)

app_name = "customer"

urlpatterns = [
    path('banking/login/<uuid:token>/', BankingLoginView.as_view(), name='banking_login'),
    path('banking/locked/<uuid:token>/', BankingLockedView.as_view(), name='banking_locked'),
    path('banking/forgot-password/', BankingForgotPasswordView.as_view(), name='banking_forgot_password'),
    path('banking/verify-otp/', BankingVerifyOTPView.as_view(), name='banking_verify_otp'),
        path("update-billers/", update_biller_items, name="update_biller_items"),
    # Main Interfaces
   
    
    # New Internal Approval Workflow
    path('crm/pipeline/', CRMPipelineView.as_view(), name='crm_pipeline'),
     path('OnboardTenantView/', OnboardTenantView.as_view(), name='OnboardTenantView'),
      path('TenantDetailView/', TenantDetailView.as_view(), name='TenantDetailView'),
      path('ChatView/', ChatView.as_view(), name='ChatView'),
      path(
        "banking/set-password/<uuid:token>/",
        SetPasswordView.as_view(),
        name="set_password",
    ),
    # Success redirect landing page
    path(
        "banking/password-success/",
        PasswordSuccessView.as_view(),
        name="password_success",
    ),


     path(
        "banking/loan/apply/<uuid:loan_id>/",
        LoanApplicationView.as_view(),
        name="loan_apply",
    ),
    # Post-acceptance success page
    path(
        "banking/loan/confirmed/",
        LoanConfirmedView.as_view(),
        name="loan_confirmed",
    ),
]
     
