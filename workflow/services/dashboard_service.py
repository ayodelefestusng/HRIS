from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import logging
from workflow.models import WorkflowInstance, Delegation
from org.models import JobRole
from org.views import log_with_context
from .workflow_service import WorkflowService

logger = logging.getLogger(__name__)

AUTHORITY_WEIGHTS = {
    "REVIEWER": 1,
    "CONCURRENCE": 2,
    "APPROVER": 3,
    "SNMGT": 4,
    "EXCO": 5,
    "BOARD": 6,
}

class WorkflowDashboardService:
    def __init__(self, employee, tenant):
        self.employee = employee
        self.tenant = tenant
        self.workflow_service = WorkflowService(tenant)
        
    def get_authority_weight(self, role):
        """Instance method to calculate weight for a specific role."""
        try:
            if not role:
                return 0
            return AUTHORITY_WEIGHTS.get(role.authority_level, 0)
        except Exception as e:
            logger.error(f"Error getting authority weight: {e}")
            return 0

    def get_employee_roles(self):
        try:
            return JobRole.objects.filter(
                employee=self.employee, org_unit__tenant=self.tenant
            ).select_related("org_unit", "job_title")
        except Exception as e:
            msg = f"Error fetching roles for employee {self.employee}: {e}"
            logger.error(msg)
            return JobRole.objects.none()

    
        

    def get_pending_actions(self):
        try:
            # 1. Get the actual Job Titles/Roles associated with this employee
            roles = self.employee.roles.all() 
            
            # 2. Get authority weights
            my_weights = [
                self.get_authority_weight(r) 
                for r in roles if self.get_authority_weight(r) > 0
            ]

            # 3. Build the Base Query
            # We look for anything that MIGHT be for this user
            query = (
                Q(current_stage__approver_type__job_role__in=roles) |
                Q(current_stage__required_authority_weight__in=my_weights) |
                Q(current_stage__approver_type__name__icontains="Manager")
            )

            active_instances = WorkflowInstance.objects.filter(
                tenant=self.tenant, 
                completed_at__isnull=True
            ).filter(query).select_related(
                "current_stage", "workflow", "initiated_by"
            ).distinct()

            # 4. Filter down to what is SPECIFICALLY for this user
            # This handles the "Manager Chain" logic where many might match the 
            # role 'Manager', but only one is the 'Line Manager'.
            pending_for_me = []
            for inst in active_instances:
                try:
                    assigned_approver = self.workflow_service.get_approver(inst, inst.current_stage)
                    
                    # Direct Match
                    if assigned_approver == self.employee:
                        pending_for_me.append(inst)
                    # Delegation Match
                    elif self._is_delegate_for(assigned_approver):
                        pending_for_me.append(inst)
                        
                except Exception as inner_e:
                    logger.error(f"Error resolving approver for {inst.id}: {inner_e}")
                    continue

            return pending_for_me

        except Exception as e:
            logger.error(f"Failed to get pending actions: {str(e)}", exc_info=True)
            return []

    
    def _is_user_authorized(self, instance, delegator_ids):
        """
        Checks if employee is the direct approver or a delegatee.
        """
        target = instance.target
        initiator_manager = getattr(target.employee, "line_manager", None)

        is_direct = initiator_manager == self.employee
        is_delegated = initiator_manager and initiator_manager.id in delegator_ids

        return is_direct or is_delegated


    
    def _is_delegate_for(self, approver):
        try:
            if not approver:
                return False

            delegation = Delegation.objects.filter(
                delegator__in=approver,
                delegatee=self.employee,
                is_active=True,
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date(),
            ).first()
            return bool(delegation)
        except Exception as e:
            logger.error(f"Error checking delegation: {e}")
            return False
    
    

    

    def get_stats_summary(self):
        try:
            pending = self.get_pending_actions()
            # Threshold for "Overdue" (e.g., older than 3 days)
            overdue_threshold = timezone.now() - timedelta(days=3)

            return {
                "total_pending": len(pending),
                "overdue": sum(1 for i in pending if i.created_at < overdue_threshold),
                "delegated_to_me": sum(1 for i in pending if not self._is_direct_approver(i)),
            }
        except Exception as e:
            logger.error(f"Error generating stats: {e}")
            return {"total_pending": 0, "overdue": 0, "delegated_to_me": 0}

    def _is_direct_approver(self, instance):
        """Helper for stats to differentiate own tasks from delegated ones."""
        try:
            return self.workflow_service.get_approver(instance, instance.current_stage) == self.employee
        except:
            return False