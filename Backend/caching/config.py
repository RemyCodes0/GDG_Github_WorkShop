"""Builds Django's CACHES setting from environment variables.

CACHE_URL picks the backend, so the same code runs everywhere:

    (unset) or locmem://       in-process memory. Default for development and tests
    redis://host:6379/0        Redis, shared by every server process. Use in production
    rediss://host:6380/0       Redis over TLS
    dummy://                   caching turned off, useful when debugging stale data

Redis needs the `redis` package (`pip install redis`). It is only imported when a redis URL
is configured, so local development has no extra dependency.
"""
from urllib.parse import urlparse

DEFAULT_TIMEOUT = 300


def build_caches(cache_url=None, default_timeout=DEFAULT_TIMEOUT, key_prefix="aubcollab"):
    url = (cache_url or "locmem://").strip()
    scheme = urlparse(url).scheme.lower()

    if scheme in ("redis", "rediss"):
        backend = {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": url,
        }
    elif scheme == "dummy":
        backend = {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}
    elif scheme == "locmem":
        backend = {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": urlparse(url).netloc or "aubcollab-default",
        }
    else:
        raise ValueError(
            f"Unsupported CACHE_URL scheme {scheme!r}. Use locmem://, redis://, rediss:// or dummy://"
        )

    backend.update({"TIMEOUT": default_timeout, "KEY_PREFIX": key_prefix})
    return {"default": backend}
