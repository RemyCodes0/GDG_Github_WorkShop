"""API versioning for AUB Collab.

Every endpoint lives under a version prefix: /api/v1/..., later /api/v2/...
The version in the URL is checked against settings.REST_FRAMEWORK["ALLOWED_VERSIONS"];
anything else returns 404.

Each versioned response (see api/base.py) carries an ``API-Version`` header. When a version is listed in
``settings.API_DEPRECATED_VERSIONS`` its responses also carry ``Deprecation`` and, if a date
is given, ``Sunset`` headers (RFC 8594), plus a ``Link`` to the newest version, so clients
get a warning long before a version is removed.
"""
from datetime import date, datetime, time, timezone

from django.conf import settings
from rest_framework.versioning import URLPathVersioning


def allowed_versions():
    return list(settings.REST_FRAMEWORK.get("ALLOWED_VERSIONS", []))


def latest_version():
    versions = allowed_versions()
    return max(versions, key=lambda v: int(v.lstrip("v"))) if versions else None


def deprecated_versions():
    return getattr(settings, "API_DEPRECATED_VERSIONS", {})


def http_date(value):
    """Format a date or ISO date string as an HTTP date for the Sunset header."""
    if isinstance(value, str):
        value = date.fromisoformat(value)
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, time.min, tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


class AUBCollabVersioning(URLPathVersioning):
    """Reads the version from the ``version`` URL kwarg, for example /api/v1/."""

    invalid_version_message = "This API version does not exist. See /api/ for the available versions."
