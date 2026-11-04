import json
import logging
from unittest import mock

from django.db import OperationalError, connections
from django.test import SimpleTestCase, TestCase, override_settings

from .context import clean_request_id, get_request_id, reset_request_id, set_request_id
from .logging import JsonFormatter, RequestIdFilter


class RequestIdTests(TestCase):
    def test_new_request_id_is_returned(self):
        response = self.client.get("/api/health/")

        self.assertRegex(response["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_incoming_request_id_is_reused(self):
        response = self.client.get("/api/health/", HTTP_X_REQUEST_ID="frontend-abc.123")

        self.assertEqual(response["X-Request-ID"], "frontend-abc.123")

    def test_unsafe_incoming_request_id_is_replaced(self):
        response = self.client.get("/api/health/", HTTP_X_REQUEST_ID="bad id\nInjected: header")

        self.assertRegex(response["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_each_request_gets_its_own_id(self):
        first = self.client.get("/api/health/")["X-Request-ID"]
        second = self.client.get("/api/health/")["X-Request-ID"]

        self.assertNotEqual(first, second)

    def test_request_id_is_cleared_after_the_request(self):
        self.client.get("/api/health/")

        self.assertIsNone(get_request_id())

    def test_server_timing_header(self):
        response = self.client.get("/api/health/")

        self.assertRegex(response["Server-Timing"], r"^app;dur=\d+\.\d$")

    def test_404_also_gets_request_id(self):
        with self.assertLogs("aubcollab.request", level="WARNING"):
            response = self.client.get("/no-such-page/")

        self.assertEqual(response.status_code, 404)
        self.assertIn("X-Request-ID", response)


class AccessLogTests(TestCase):
    def test_request_is_logged_with_details(self):
        with self.assertLogs("aubcollab.request", level="INFO") as logs:
            self.client.get("/admin/login/", HTTP_X_REQUEST_ID="trace-1")

        record = logs.records[0]
        self.assertEqual(record.levelno, logging.INFO)
        self.assertEqual(record.http_method, "GET")
        self.assertEqual(record.path, "/admin/login/")
        self.assertEqual(record.status, 200)
        self.assertIsNone(record.user_id)
        self.assertGreaterEqual(record.duration_ms, 0)

    def test_client_errors_log_as_warning(self):
        with self.assertLogs("aubcollab.request", level="WARNING") as logs:
            self.client.get("/no-such-page/")

        self.assertEqual(logs.records[0].levelno, logging.WARNING)

    def test_health_probes_log_quietly(self):
        with self.assertLogs("aubcollab.request", level="DEBUG") as logs:
            self.client.get("/api/health/")

        self.assertEqual(logs.records[0].levelno, logging.DEBUG)

    @override_settings(OBSERVABILITY_SLOW_REQUEST_MS=0)
    def test_slow_requests_are_flagged(self):
        with self.assertLogs("aubcollab.request", level="WARNING") as logs:
            self.client.get("/admin/login/")

        self.assertTrue(logs.records[0].slow)


class ProbeTests(TestCase):
    def test_liveness(self):
        response = self.client.get("/api/health/live/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_readiness_checks_the_database(self):
        response = self.client.get("/api/health/ready/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["checks"]["database:default"]["status"], "ok")
        self.assertEqual(body["request_id"], response["X-Request-ID"])

    def test_readiness_returns_503_when_database_is_down(self):
        with mock.patch.object(
            type(connections["default"]), "cursor", side_effect=OperationalError("database is down")
        ), self.assertLogs("aubcollab.health", level="ERROR"):
            response = self.client.get("/api/health/ready/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertEqual(response.json()["checks"]["database:default"]["error"], "OperationalError")


class LoggingFormatTests(SimpleTestCase):
    def _record(self, **extra):
        record = logging.LogRecord("aubcollab.test", logging.INFO, __file__, 1, "hello %s", ("world",), None)
        for key, value in extra.items():
            setattr(record, key, value)
        return record

    def test_filter_adds_request_id(self):
        token = set_request_id("abc123")
        try:
            record = self._record()
            RequestIdFilter().filter(record)
        finally:
            reset_request_id(token)

        self.assertEqual(record.request_id, "abc123")

    def test_filter_uses_dash_outside_a_request(self):
        record = self._record()
        RequestIdFilter().filter(record)

        self.assertEqual(record.request_id, "-")

    def test_json_formatter_outputs_one_json_object(self):
        record = self._record(request_id="abc123", status=200, duration_ms=4.2)
        payload = json.loads(JsonFormatter().format(record))

        self.assertEqual(payload["message"], "hello world")
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["logger"], "aubcollab.test")
        self.assertEqual(payload["request_id"], "abc123")
        self.assertEqual(payload["status"], 200)
        self.assertEqual(payload["duration_ms"], 4.2)
        self.assertIn("timestamp", payload)

    def test_json_formatter_includes_exceptions(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord("x", logging.ERROR, __file__, 1, "failed", (), sys.exc_info())
        payload = json.loads(JsonFormatter().format(record))

        self.assertIn("ValueError: boom", payload["exception"])

    def test_clean_request_id(self):
        self.assertEqual(clean_request_id("abc-123"), "abc-123")
        self.assertRegex(clean_request_id(None), r"^[0-9a-f]{32}$")
        self.assertRegex(clean_request_id("x" * 200), r"^[0-9a-f]{32}$")
