import logging

class ContextFilter(logging.Filter):
    def filter(self, record):
        # Default values
        record.tenant = "N/A"
        record.user_email = "Anonymous"

        # If the record has a request attached (via your log_with_context helper or middleware)
        request = getattr(record, "request", None)
        if request and hasattr(request, "user"):
            user = request.user
            record.tenant = getattr(user, "tenant", "N/A")
            record.user_email = getattr(user, "email", "Anonymous")

        return True