import logging
from .workflow_service import WorkflowService
from .dashboard_service import WorkflowDashboardService

# Re-exporting for backward compatibility
# Any code importing form workflow.services.workflow_engine will now get these classes
# from the new files.

__all__ = ["WorkflowService", "WorkflowDashboardService", "AUTHORITY_WEIGHTS"]

from .dashboard_service import AUTHORITY_WEIGHTS
