import threading

# Global thread-local storage for request data
_thread_locals = threading.local()


def get_current_request():
    """Return the request object for the current thread."""
    return getattr(_thread_locals, "request", None)


def get_current_user():
    """Return the user object for the current thread."""
    return getattr(_thread_locals, "user", None)


class ThreadLocalMiddleware:
    """
    Middleware that puts the request object in thread local storage.
    This allows logging filters to access request data (user, tenant).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        _thread_locals.user = getattr(request, "user", None)
        # Store simple strings for logging to avoid db hits in filter
        if request.user and request.user.is_authenticated:
            _thread_locals.user_str = request.user.email
            # Handle Tenant
            tenant = getattr(request.user, "tenant", None)
            if tenant:
                _thread_locals.tenant_str = str(tenant.name)
            else:
                _thread_locals.tenant_str = "No-Tenant"
        else:
            _thread_locals.user_str = "Anonymous"
            _thread_locals.tenant_str = "Public"

        try:
            response = self.get_response(request)
        finally:
            # Cleanup to prevent data leaking to other requests in the same thread
            _thread_locals.request = None
            _thread_locals.user = None
            _thread_locals.user_str = None
            _thread_locals.tenant_str = None

        return response
