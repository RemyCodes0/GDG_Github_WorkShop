"""Request tracing middleware.

For every request it:
  * picks a request ID (from the X-Request-ID header, or a new one) and returns it in the response
  * measures how long the request took and returns it in a Server-Timing header
  * writes one structured access log line: method, path, status, duration, user
  * flags slow requests (OBSERVABILITY_SLOW_REQUEST_MS) and server errors at a higher log level
"""
import logging
import time

from django.conf import settings

from .context import REQUEST_ID_HEADER, clean_request_id, reset_request_id, set_request_id

logger = logging.getLogger("aubcollab.request")

# Health probes run every few seconds in production; logging them at INFO drowns real traffic.
QUIET_PATH_PREFIXES = ("/api/health",)


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = clean_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.request_id = request_id
        token = set_request_id(request_id)
        start = time.perf_counter()
        try:
            response = self.get_response(request)
            duration_ms = (time.perf_counter() - start) * 1000
            response[REQUEST_ID_HEADER] = request_id
            response["Server-Timing"] = f"app;dur={duration_ms:.1f}"
            self._log(request, response.status_code, duration_ms)
            return response
        finally:
            reset_request_id(token)

    def _log(self, request, status_code, duration_ms):
        slow_ms = getattr(settings, "OBSERVABILITY_SLOW_REQUEST_MS", 1000)
        if status_code >= 500:
            level = logging.ERROR
        elif duration_ms >= slow_ms:
            level = logging.WARNING
        elif status_code >= 400:
            level = logging.WARNING
        elif request.path.startswith(QUIET_PATH_PREFIXES):
            level = logging.DEBUG
        else:
            level = logging.INFO

        user = getattr(request, "user", None)
        logger.log(
            level,
            "%s %s %s %.1fms",
            request.method,
            request.path,
            status_code,
            duration_ms,
            extra={
                "http_method": request.method,
                "path": request.path,
                "status": status_code,
                "duration_ms": round(duration_ms, 1),
                "slow": duration_ms >= slow_ms,
                "user_id": user.pk if user is not None and user.is_authenticated else None,
            },
        )
