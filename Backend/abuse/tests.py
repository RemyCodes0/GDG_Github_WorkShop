from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import path
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from .throttles import (
    AnonBurstThrottle,
    AnonSustainedThrottle,
    SensitiveActionThrottle,
    UserBurstThrottle,
    UserSustainedThrottle,
)

GLOBAL_THROTTLES = [AnonBurstThrottle, AnonSustainedThrottle, UserBurstThrottle, UserSustainedThrottle]

TEST_RATES = {
    "anon_burst": "3/min",
    "anon_sustained": "100/day",
    "user_burst": "5/min",
    "user_sustained": "100/day",
    "auth": "2/min",
}


class OpenView(APIView):
    throttle_classes = GLOBAL_THROTTLES

    def get(self, request):
        return Response({"ok": True})


class LoginView(APIView):
    throttle_classes = [*GLOBAL_THROTTLES, SensitiveActionThrottle]
    throttle_scope = "auth"

    def post(self, request):
        return Response({"ok": True})


class RegisterView(LoginView):
    pass


urlpatterns = [
    path("open/", OpenView.as_view()),
    path("login/", LoginView.as_view()),
    path("register/", RegisterView.as_view()),
]


@override_settings(ROOT_URLCONF="abuse.tests")
class ThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        patcher = mock.patch.object(SimpleRateThrottle, "THROTTLE_RATES", TEST_RATES)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_anonymous_burst_limit(self):
        for _ in range(3):
            self.assertEqual(self.client.get("/open/").status_code, 200)

        with self.assertLogs("aubcollab.abuse", level="WARNING"):
            response = self.client.get("/open/")

        self.assertEqual(response.status_code, 429)

    def test_rate_limited_response_is_helpful(self):
        for _ in range(3):
            self.client.get("/open/")
        with self.assertLogs("aubcollab.abuse", level="WARNING"):
            response = self.client.get("/open/")

        body = response.json()
        self.assertEqual(body["code"], "rate_limited")
        self.assertGreater(body["retry_after_seconds"], 0)
        self.assertEqual(response["Retry-After"], str(body["retry_after_seconds"]))

    def test_limits_are_per_ip(self):
        for _ in range(3):
            self.client.get("/open/", REMOTE_ADDR="10.0.0.1")

        response = self.client.get("/open/", REMOTE_ADDR="10.0.0.2")

        self.assertEqual(response.status_code, 200)

    def test_signed_in_users_get_their_own_higher_limit(self):
        user = get_user_model().objects.create_user("student", password="unused-test-password")
        self.client.force_login(user)

        statuses = [self.client.get("/open/").status_code for _ in range(5)]
        with self.assertLogs("aubcollab.abuse", level="WARNING") as logs:
            sixth = self.client.get("/open/")

        self.assertEqual(statuses, [200] * 5)
        self.assertEqual(sixth.status_code, 429)
        self.assertEqual(logs.records[0].user_id, user.pk)
        self.assertEqual(logs.records[0].throttle_scope, "user_burst")

    def test_sensitive_actions_have_a_tighter_limit(self):
        self.assertEqual(self.client.post("/login/").status_code, 200)
        self.assertEqual(self.client.post("/login/").status_code, 200)

        with self.assertLogs("aubcollab.abuse", level="WARNING") as logs:
            response = self.client.post("/login/")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(logs.records[0].throttle_scope, "auth")

    def test_sensitive_limit_is_shared_across_endpoints_in_a_scope(self):
        self.client.post("/login/")
        self.client.post("/register/")

        with self.assertLogs("aubcollab.abuse", level="WARNING"):
            response = self.client.post("/login/")

        self.assertEqual(response.status_code, 429)

    def test_rejections_are_logged_with_context(self):
        for _ in range(3):
            self.client.get("/open/", REMOTE_ADDR="10.9.9.9")
        with self.assertLogs("aubcollab.abuse", level="WARNING") as logs:
            self.client.get("/open/", REMOTE_ADDR="10.9.9.9")

        record = logs.records[0]
        self.assertEqual(record.client_ip, "10.9.9.9")
        self.assertEqual(record.path, "/open/")
        self.assertIsNone(record.user_id)


class SettingsTests(TestCase):
    def test_default_throttles_are_configured(self):
        from django.conf import settings

        rest = settings.REST_FRAMEWORK
        self.assertIn("abuse.throttles.AnonBurstThrottle", rest["DEFAULT_THROTTLE_CLASSES"])
        for scope in ("anon_burst", "anon_sustained", "user_burst", "user_sustained", "auth", "applications"):
            self.assertIn(scope, rest["DEFAULT_THROTTLE_RATES"])
        self.assertEqual(rest["EXCEPTION_HANDLER"], "abuse.handlers.api_exception_handler")

    def test_oversized_bodies_are_rejected(self):
        from django.core.exceptions import RequestDataTooBig
        from django.test import RequestFactory

        request = RequestFactory().post("/any/", data="x" * (3 * 1024 * 1024), content_type="text/plain")

        with self.assertRaises(RequestDataTooBig):
            request.body
