# core/middleware.py
import time
from .models import RequestLog

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = int((time.time() - start) * 1000)

        if request.path.startswith('/v1/'):
            RequestLog.objects.create(
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                response_time_ms=duration,
                ip_address=request.META.get('REMOTE_ADDR'),
                user=request.user if request.user.is_authenticated else None,
            )

        return response