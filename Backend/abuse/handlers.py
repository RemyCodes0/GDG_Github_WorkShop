"""API exception handler that makes 429 responses friendly and machine readable."""
import math

from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None and isinstance(exc, Throttled):
        wait = math.ceil(exc.wait) if exc.wait is not None else None
        response.data = {
            "detail": "Too many requests. Please slow down and try again later.",
            "code": "rate_limited",
            "retry_after_seconds": wait,
        }
        if wait is not None:
            response["Retry-After"] = str(wait)
    return response
