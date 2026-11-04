from django.test import TestCase, override_settings
from django.urls import reverse


class ApiRootTests(TestCase):
    def test_lists_available_versions(self):
        response = self.client.get("/api/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["latest"], "v1")
        self.assertEqual(body["versions"][0]["version"], "v1")
        self.assertEqual(body["versions"][0]["status"], "supported")
        self.assertTrue(body["versions"][0]["url"].endswith("/api/v1/"))

    @override_settings(API_DEPRECATED_VERSIONS={"v1": {"sunset": "2027-09-01"}})
    def test_marks_deprecated_versions(self):
        body = self.client.get("/api/").json()

        self.assertEqual(body["versions"][0]["status"], "deprecated")
        self.assertEqual(body["versions"][0]["sunset"], "2027-09-01")


class VersionedHealthTests(TestCase):
    def test_v1_health(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "version": "v1"})
        self.assertEqual(response["API-Version"], "v1")

    def test_url_can_be_reversed_by_namespace(self):
        self.assertEqual(reverse("v1:health", kwargs={"version": "v1"}), "/api/v1/health/")

    def test_supported_version_has_no_deprecation_headers(self):
        response = self.client.get("/api/v1/health/")

        self.assertNotIn("Deprecation", response)
        self.assertNotIn("Sunset", response)

    def test_legacy_unversioned_health_still_works(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class UnknownVersionTests(TestCase):
    def test_unknown_version_returns_json_404(self):
        response = self.client.get("/api/v99/health/")

        self.assertEqual(response.status_code, 404)
        self.assertIn("version", response.json()["detail"].lower())

    def test_unknown_version_rejected_for_every_method(self):
        response = self.client.post("/api/v2/projects/", {})

        self.assertEqual(response.status_code, 404)

    def test_unknown_path_in_real_version_returns_json_404(self):
        response = self.client.get("/api/v1/does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertIn("detail", response.json())


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_VERSIONING_CLASS": "api.versioning.AUBCollabVersioning",
        "DEFAULT_VERSION": "v1",
        "ALLOWED_VERSIONS": ["v1", "v2"],
        "VERSION_PARAM": "version",
    },
    API_DEPRECATED_VERSIONS={"v1": {"sunset": "2027-09-01"}},
)
class DeprecationHeaderTests(TestCase):
    def test_deprecated_version_gets_warning_headers(self):
        response = self.client.get("/api/v1/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Deprecation"], "true")
        self.assertEqual(response["Sunset"], "Wed, 01 Sep 2027 00:00:00 GMT")
        self.assertEqual(response["Link"], '</api/v2/>; rel="successor-version"')
