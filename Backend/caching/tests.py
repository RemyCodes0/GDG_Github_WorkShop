from io import StringIO
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from .config import build_caches
from .utils import cached, get_or_set, invalidate, make_key, namespace_version


class BuildCachesTests(SimpleTestCase):
    def test_defaults_to_local_memory(self):
        caches = build_caches(None)

        self.assertEqual(caches["default"]["BACKEND"], "django.core.cache.backends.locmem.LocMemCache")
        self.assertEqual(caches["default"]["TIMEOUT"], 300)
        self.assertEqual(caches["default"]["KEY_PREFIX"], "aubcollab")

    def test_redis_url(self):
        caches = build_caches("redis://cache.internal:6379/1", default_timeout=60)

        self.assertEqual(caches["default"]["BACKEND"], "django.core.cache.backends.redis.RedisCache")
        self.assertEqual(caches["default"]["LOCATION"], "redis://cache.internal:6379/1")
        self.assertEqual(caches["default"]["TIMEOUT"], 60)

    def test_redis_over_tls(self):
        caches = build_caches("rediss://cache.internal:6380/0")

        self.assertEqual(caches["default"]["BACKEND"], "django.core.cache.backends.redis.RedisCache")

    def test_dummy_turns_caching_off(self):
        caches = build_caches("dummy://")

        self.assertEqual(caches["default"]["BACKEND"], "django.core.cache.backends.dummy.DummyCache")

    def test_unknown_scheme_is_rejected(self):
        with self.assertRaises(ValueError):
            build_caches("memcached://localhost:11211")


class CacheHelperTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_get_or_set_computes_once(self):
        compute = mock.Mock(return_value=["project"])

        first = get_or_set("projects", ("list",), compute)
        second = get_or_set("projects", ("list",), compute)

        self.assertEqual(first, ["project"])
        self.assertEqual(second, ["project"])
        compute.assert_called_once()

    def test_cached_values_can_be_falsy(self):
        compute = mock.Mock(return_value=[])

        get_or_set("projects", ("empty",), compute)
        get_or_set("projects", ("empty",), compute)

        compute.assert_called_once()

    def test_invalidate_makes_old_keys_stale(self):
        compute = mock.Mock(side_effect=["old", "new"])

        self.assertEqual(get_or_set("projects", ("list",), compute), "old")
        invalidate("projects")
        self.assertEqual(get_or_set("projects", ("list",), compute), "new")

    def test_invalidate_only_affects_its_namespace(self):
        projects = mock.Mock(return_value="p")
        profiles = mock.Mock(return_value="u")
        get_or_set("projects", ("list",), projects)
        get_or_set("profiles", ("list",), profiles)

        invalidate("projects")
        get_or_set("projects", ("list",), projects)
        get_or_set("profiles", ("list",), profiles)

        self.assertEqual(projects.call_count, 2)
        self.assertEqual(profiles.call_count, 1)

    def test_invalidate_before_first_use(self):
        self.assertEqual(invalidate("never-used"), 2)
        self.assertEqual(namespace_version("never-used"), 2)

    def test_keys_are_short_and_versioned(self):
        key = make_key("projects", "a very long argument " * 50, page=2)

        self.assertTrue(key.startswith("projects:v1:"))
        self.assertLess(len(key), 64)
        self.assertEqual(key, make_key("projects", "a very long argument " * 50, page=2))
        self.assertNotEqual(key, make_key("projects", "a very long argument " * 50, page=3))

    def test_broken_cache_falls_back_to_computing(self):
        compute = mock.Mock(return_value="fresh")

        with mock.patch("caching.utils.cache.get", side_effect=ConnectionError("cache down")), self.assertLogs(
            "aubcollab.cache", level="WARNING"
        ):
            self.assertEqual(get_or_set("projects", ("list",), compute), "fresh")

    def test_failed_write_still_returns_value(self):
        with mock.patch("caching.utils.cache.set", side_effect=ConnectionError("cache down")), self.assertLogs(
            "aubcollab.cache", level="WARNING"
        ):
            self.assertEqual(get_or_set("projects", ("list",), lambda: 42), 42)


class CachedDecoratorTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_caches_per_arguments(self):
        calls = []

        @cached("projects")
        def project_list(category=None):
            calls.append(category)
            return f"projects in {category}"

        self.assertEqual(project_list(category="Research"), "projects in Research")
        self.assertEqual(project_list(category="Research"), "projects in Research")
        self.assertEqual(project_list(category="Design"), "projects in Design")
        self.assertEqual(calls, ["Research", "Design"])

    def test_per_object_namespace(self):
        calls = []

        @cached(lambda user_id: f"profile:{user_id}")
        def profile(user_id):
            calls.append(user_id)
            return {"id": user_id}

        profile(1)
        profile(2)
        profile.invalidate(1)
        profile(1)
        profile(2)

        self.assertEqual(calls, [1, 2, 1])


class CacheCheckCommandTests(SimpleTestCase):
    def test_reports_ok(self):
        out = StringIO()
        call_command("cachecheck", stdout=out)

        self.assertIn("LocMemCache: OK", out.getvalue())

    @override_settings(CACHES=build_caches("dummy://"))
    def test_warns_when_caching_is_off(self):
        out = StringIO()
        call_command("cachecheck", stdout=out)

        self.assertIn("turned off", out.getvalue())

    def test_fails_when_cache_is_unreachable(self):
        with mock.patch("caching.management.commands.cachecheck.cache.set", side_effect=ConnectionError("refused")):
            with self.assertRaises(CommandError):
                call_command("cachecheck", stdout=StringIO())
