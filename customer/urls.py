from django.urls import path
from .views import (
    CRMPipelineView,
)

app_name = "customer"

urlpatterns = [
    # Main Interfaces
   
    
    # New Internal Approval Workflow
    path('crm/pipeline/', CRMPipelineView.as_view(), name='crm_pipeline'),
]
