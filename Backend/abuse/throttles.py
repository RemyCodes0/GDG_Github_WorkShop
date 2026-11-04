"""Rate limits for the API, built on Django REST Framework throttling.

Every request goes through two global limits, one short (burst) and one long (sustained),
counted per IP address for anonymous visitors and per account for signed in users:

    anon_burst / anon_sustained   e.g. 30 per minute and 500 per day per IP
    user_burst / user_sustained   e.g. 120 per minute and 5000 per day per account

Sensitive endpoints add a tighter, named limit on top (SensitiveActionThrottle):

    class LoginView(APIView):
        throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, SensitiveActionThrottle]
        throttle_scope = "auth"          # rates in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

Counters live in the default cache, so in production (several server processes) the cache
must be shared, for example Redis.
"""
import logging

from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle

logger = logging.getLogger("aubcollab.abuse")


class LoggedThrottleMixin:
    """Logs every rejected request so repeated abuse is visible in the logs."""

    def allow_request(self, request, view):
        allowed = super().allow_request(request, view)
        if not allowed:
            user = getattr(request, "user", None)
            logger.warning(
                "Rate limit hit: %s on %s",
                self.scope,
                request.path,
                extra={
                    "throttle_scope": self.scope,
                    "path": request.path,
                    "client_ip": self.get_ident(request),
                    "user_id": user.pk if user is not None and user.is_authenticated else None,
                    "retry_after_s": self.wait(),
                },
            )
        return allowed


class AnonBurstThrottle(LoggedThrottleMixin, AnonRateThrottle):
    scope = "anon_burst"


class AnonSustainedThrottle(LoggedThrottleMixin, AnonRateThrottle):
    scope = "anon_sustained"


class UserBurstThrottle(LoggedThrottleMixin, UserRateThrottle):
    scope = "user_burst"


class UserSustainedThrottle(LoggedThrottleMixin, UserRateThrottle):
    scope = "user_sustained"


class SensitiveActionThrottle(LoggedThrottleMixin, ScopedRateThrottle):
    """Tighter limit for a named group of endpoints, set by the view's throttle_scope.

    Counted per account when signed in and per IP otherwise, and shared by every view with
    the same scope, so splitting attempts across several endpoints does not help.
    """
