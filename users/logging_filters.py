import logging
from .middleware import _thread_locals


class ContextFilter(logging.Filter):
    """
    Injects application context (Tenant, User, App Name) into LogRecord.
    """

    def filter(self, record):
        # 1. Tenant and User from Thread Locals
        record.tenant = getattr(_thread_locals, "tenant_str", "System")
        record.user = getattr(_thread_locals, "user_str", "System-User")

        # 2. App Name Extraction
        # record.name usually looks like 'myproject.hr.views' or 'hr.views'
        # We want just 'hr' or 'payroll'
        if record.name:
            parts = record.name.split(".")
            # If starts with 'myproject', take the second part.
            if parts[0] == "myproject" and len(parts) > 1:
                record.app_name = parts[1].upper()
            else:
                record.app_name = parts[0].upper()
        else:
            record.app_name = "UNKNOWN"

        return True
