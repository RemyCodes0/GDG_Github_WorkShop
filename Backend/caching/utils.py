"""Caching helpers for AUB Collab features.

Keys are grouped into namespaces, for example "projects" or "profile:42". Each namespace has
a version number stored in the cache, and that version is part of every key in it. Bumping
the version (invalidate) makes every old key unreachable at once, without having to find and
delete them, which works the same on every backend (memory, Redis, ...). Old entries simply
expire on their own.

    from caching.utils import cached, invalidate

    @cached("projects", timeout=120)
    def project_list(category=None):
        ...

    # after a project is created, edited or deleted:
    invalidate("projects")

To turn caching off everywhere (for example while debugging stale data), set CACHE_URL=dummy://.
"""
import functools
import hashlib
import json
import logging

from django.core.cache import cache

logger = logging.getLogger("aubcollab.cache")

_VERSION_KEY = "ns-version:{namespace}"
_MISSING = object()


def namespace_version(namespace: str) -> int:
    key = _VERSION_KEY.format(namespace=namespace)
    version = cache.get(key)
    if version is None:
        # add() only writes if no other process set it first.
        cache.add(key, 1, timeout=None)
        version = cache.get(key, 1)
    return int(version)


def invalidate(namespace: str) -> int:
    """Make every key in the namespace stale. Returns the new version."""
    key = _VERSION_KEY.format(namespace=namespace)
    try:
        version = cache.incr(key)
    except ValueError:  # the version key did not exist yet
        cache.set(key, 2, timeout=None)
        version = 2
    logger.info("Invalidated cache namespace %s", namespace, extra={"namespace": namespace, "version": version})
    return version


def make_key(namespace: str, *parts, **named) -> str:
    """Build a short, safe cache key from any JSON serializable arguments."""
    raw = json.dumps([parts, named], sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return f"{namespace}:v{namespace_version(namespace)}:{digest}"


def get_or_set(namespace: str, key_parts, compute, timeout=None):
    """Return the cached value, or compute it, store it and return it.

    A cache that is down never breaks the request: errors are logged and the value is computed.
    """
    parts = key_parts if isinstance(key_parts, (list, tuple)) else (key_parts,)
    try:
        key = make_key(namespace, *parts)
        value = cache.get(key, _MISSING)
    except Exception:
        logger.warning("Cache read failed for namespace %s", namespace, exc_info=True)
        return compute()

    if value is not _MISSING:
        return value

    value = compute()
    try:
        if timeout is None:
            cache.set(key, value)
        else:
            cache.set(key, value, timeout=timeout)
    except Exception:
        logger.warning("Cache write failed for namespace %s", namespace, exc_info=True)
    return value


def cached(namespace: str, timeout=None):
    """Decorator: cache a function's return value per set of arguments, inside a namespace.

    The namespace can be a string, or a function that receives the same arguments and
    returns one, e.g. lambda user_id: f"profile:{user_id}" to invalidate one user at a time.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ns = namespace(*args, **kwargs) if callable(namespace) else namespace
            return get_or_set(
                ns,
                (func.__module__, func.__qualname__, args, kwargs),
                lambda: func(*args, **kwargs),
                timeout=timeout,
            )

        wrapper.invalidate = lambda *args, **kwargs: invalidate(
            namespace(*args, **kwargs) if callable(namespace) else namespace
        )
        return wrapper

    return decorator
