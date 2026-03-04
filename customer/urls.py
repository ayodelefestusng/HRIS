from django.urls import path
from .views import (
    CRMPipelineView,OnboardTenantView,TenantDetailView,ChatView
)

app_name = "customer"

urlpatterns = [
    # Main Interfaces
   
    
    # New Internal Approval Workflow
    path('crm/pipeline/', CRMPipelineView.as_view(), name='crm_pipeline'),
     path('OnboardTenantView/', OnboardTenantView.as_view(), name='OnboardTenantView'),
      path('TenantDetailView/', TenantDetailView.as_view(), name='TenantDetailView'),
      path('ChatView/', ChatView.as_view(), name='ChatView'),
]
     
