from rest_framework.permissions import BasePermission


class IsOwnerOrHR(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        return obj.employee == getattr(user, "employee", None)
    
    
    
from django.db import transaction
from org.models import JobRole
from workflow.models import WorkflowInstance, WorkflowAction, Workflow  
from django.utils import timezone   

def route_leave_request_for_approval(leave_request):
    """
    Routes a LeaveRequest to the appropriate approvers based on authority_level.
    Creates WorkflowAssignment records for each approver.
    """

    # Step 1: Find approvers in the same OrgUnit
    approvers = JobRole.objects.filter(
        org_unit=leave_request.employee.org_unit,   # assumes Employee has org_unit
        authority_level__in=["APPROVER", "SNMGT", "EXCO", "BOARD"],  # authority chain
        status="SUBSTANTIVE"
    ).select_related("employee")

    if not approvers.exists():
        raise ValueError("No approvers found for this OrgUnit")

    # Step 2: Create workflow assignments
    # with transaction.atomic():
        
    for role in approvers:
        WorkflowAction.objects.create(
                workflow_instance=WorkflowInstance.objects.create(
                    workflow=Workflow.objects.get(code="LEAVE_APPROVAL"),
                    tenant=leave_request.tenant,
                    target=leave_request,
                    current_stage="APPROVAL",
                ),
                approver=role.employee,
                assigned_at=timezone.now(),
                status="PENDING"
            )

    # Step 3: Update LeaveRequest status
    leave_request.status = "PENDING"
    leave_request.save(update_fields=["status"])

    return approvers