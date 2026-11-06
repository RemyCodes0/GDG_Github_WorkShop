"""Smoke tests for the project setup. They give the CI pipeline something real to run."""
from django.test import TestCase


class HealthCheckTests(TestCase):
    def test_health_returns_ok(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_only_needs_get(self):
        response = self.client.head("/api/health/")

        self.assertEqual(response.status_code, 200)


class AdminTests(TestCase):
    def test_admin_login_page_loads(self):
        response = self.client.get("/admin/login/")

        self.assertEqual(response.status_code, 200)
