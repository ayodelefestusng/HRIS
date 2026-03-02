# org/managers.py
from django.db import models
from users.middleware import _thread_locals

class TenantManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        
        # If the thread has a tenant_id, filter by it automatically
        tenant_id = getattr(_thread_locals, 'tenant_id', None)
        
        # We skip filtering for superusers or if no tenant is set (e.g. background tasks)
        if tenant_id and not getattr(_thread_locals, 'is_superuser', False):
            return qs.filter(tenant_id=tenant_id)
        
        return qs