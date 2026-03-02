import threading

# Global thread-local storage for request data
_thread_locals = threading.local()

# users/middleware.py
class TenantLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set values for the manager and the logger
        _thread_locals.tenant_id = getattr(request.user, 'tenant_id', None)
        _thread_locals.user_id = request.user.id if request.user.is_authenticated else 'Anonymous'
        _thread_locals.is_superuser = request.user.is_superuser if request.user.is_authenticated else False
        
        response = self.get_response(request)
        
        # Clear after request to prevent memory leaks or cross-contamination
        _thread_locals.tenant_id = None
        _thread_locals.is_superuser = False
        
        return response