from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from .deploy import build_databases, env_bool, env_list, https_settings

BASE = Path("/srv/app")


class DatabaseConfigTests(SimpleTestCase):
    def test_sqlite_by_default(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            db = build_databases(BASE)["default"]

        self.assertEqual(db["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(db["NAME"], str(BASE / "db.sqlite3"))

    def test_postgres_from_environment(self):
        env = {
            "DB_ENGINE": "postgres",
            "DB_NAME": "collab",
            "DB_USER": "svc",
            "DB_PASSWORD": "secret",
            "DB_HOST": "db",
            "DB_PORT": "6543",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            db = build_databases(BASE)["default"]

        self.assertEqual(db["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual((db["NAME"], db["USER"], db["HOST"], db["PORT"]), ("collab", "svc", "db", "6543"))
        self.assertEqual(db["CONN_MAX_AGE"], 60)
        self.assertTrue(db["CONN_HEALTH_CHECKS"])

    def test_unknown_engine_is_rejected(self):
        with mock.patch.dict("os.environ", {"DB_ENGINE": "oracle"}, clear=True):
            with self.assertRaises(ValueError):
                build_databases(BASE)


class HttpsSettingsTests(SimpleTestCase):
    def test_off_by_default(self):
        self.assertEqual(https_settings(False), {})

    def test_on_enables_secure_cookies_redirect_and_hsts(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            values = https_settings(True)

        self.assertTrue(values["SESSION_COOKIE_SECURE"])
        self.assertTrue(values["CSRF_COOKIE_SECURE"])
        self.assertTrue(values["SECURE_SSL_REDIRECT"])
        self.assertEqual(values["SECURE_HSTS_SECONDS"], 3600)
        self.assertEqual(values["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertIn(r"^api/health/", values["SECURE_REDIRECT_EXEMPT"])

    def test_redirect_can_be_left_to_the_proxy(self):
        with mock.patch.dict("os.environ", {"DJANGO_SECURE_SSL_REDIRECT": "false"}, clear=True):
            self.assertFalse(https_settings(True)["SECURE_SSL_REDIRECT"])


class EnvHelperTests(SimpleTestCase):
    def test_env_bool(self):
        with mock.patch.dict("os.environ", {"A": "yes", "B": "0"}, clear=True):
            self.assertTrue(env_bool("A"))
            self.assertFalse(env_bool("B"))
            self.assertTrue(env_bool("MISSING", default=True))

    def test_env_list_ignores_blanks(self):
        with mock.patch.dict("os.environ", {"HOSTS": "a.edu, b.edu,,"}, clear=True):
            self.assertEqual(env_list("HOSTS"), ["a.edu", "b.edu"])
