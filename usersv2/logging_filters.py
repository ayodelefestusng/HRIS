import logging
from .middleware import _thread_locals

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.tenant_id = getattr(_thread_locals, 'tenant_id', 'N/A')
        record.user_id = getattr(_thread_locals, 'user_id', 'N/A')
        return True