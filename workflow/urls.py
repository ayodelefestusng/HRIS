from django.urls import path
from .views import (
    WorkflowInboxView,
    HistoryView,
    WorkflowDetailView,
    ProcessActionView,
    DelegateView,
    batch_workflow_action,
    confirm_resumption,
    ProfileUpdateApprovalView,
    FinalizeUpdateActionView,
    BatchActionView,
    WorkflowActionView,
    WorkflowResubmitView,
    ApprovalHubView,
    InternalDocumentCreateView,
    InternalDocumentDetailView,
    InternalDocumentDetailView,
    ReviewerEditView,
    internal_document_fields,
    ProcurementDashboardView,
)

app_name = "workflow"

urlpatterns = [
    # Main Interfaces
    path("inbox/", WorkflowInboxView.as_view(), name="inbox"),
    path("history/", HistoryView.as_view(), name="history"),
    # Detail & Actions
    path("request/<int:pk>/", WorkflowDetailView.as_view(), name="detail"),
    path(
        "request/<int:pk>/action/", WorkflowActionView.as_view(), name="process_action"
    ),
    
    
    
    
    # path(
    #     "request/<int:pk>/action/", ProcessActionView.as_view(), name="process_action"
    # ),
    # Utilities
    path("delegate/", DelegateView.as_view(), name="delegate"),
    
    # path('inbox/', views.InboxView.as_view(), name='inbox'),
    # path('batch-action/', batch_workflow_action, name='batch_action'),
    path('confirm-resumption/<int:pk>/', confirm_resumption, name='confirm_resumption'),


# path("workflow/inbox/", WorkflowInboxView.as_view(), name="inbox"),
# Batch processing for the checkbox-based UI
    path('batch-action/', BatchActionView.as_view(), name='batch_action'),
path("workflow/approve-profile/<int:pk>/", ProfileUpdateApprovalView.as_view(), name="approve_profile"),
path("workflow/finalize/<int:pk>/", FinalizeUpdateActionView.as_view(), name="finalize"),

# workflow/urls.py
path('detail/<int:pk>/', WorkflowDetailView.as_view(), name='inbox_detail'), # Name is 'detail'


path('resubmit/<int:pk>/', WorkflowResubmitView.as_view(), name='resubmit_detail'),

    # New Internal Approval Workflow
    path('approval-hub/', ApprovalHubView.as_view(), name='approval_hub'),
    path('internal-document/create/', InternalDocumentCreateView.as_view(), name='internal_document_create'),
    path('internal-document/<int:pk>/', InternalDocumentDetailView.as_view(), name='internal_document_detail'),
    path('internal-document/<int:pk>/edit/', ReviewerEditView.as_view(), name='reviewer_edit'),
    path('internal-document/fields/', internal_document_fields, name='internal_document_fields'),
    path('procurement/dashboard/', ProcurementDashboardView.as_view(), name='procurement_dashboard'),
]
