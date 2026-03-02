import logging

class RequestLoggingMiddleware:
    """
    Attaches the request object to log records so filters can use it.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logging.LoggerAdapter(logging.getLogger(), {"request": request})
        response = self.get_response(request)
        return response