"""Production settings helpers, driven by environment variables so one image runs anywhere."""
import os

TRUE_VALUES = {"1", "true", "yes", "on"}


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def build_databases(base_dir):
    """SQLite by default. DB_ENGINE=postgres switches to PostgreSQL using the DB_* variables."""
    engine = os.environ.get("DB_ENGINE", "sqlite").lower()
    if engine in ("postgres", "postgresql"):
        return {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": os.environ.get("DB_NAME", "aubcollab"),
                "USER": os.environ.get("DB_USER", "aubcollab"),
                "PASSWORD": os.environ.get("DB_PASSWORD", ""),
                "HOST": os.environ.get("DB_HOST", "localhost"),
                "PORT": os.environ.get("DB_PORT", "5432"),
                # Reuse connections between requests instead of reconnecting every time.
                "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
                "CONN_HEALTH_CHECKS": True,
            }
        }
    if engine == "sqlite":
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": os.environ.get("DB_NAME", str(base_dir / "db.sqlite3")),
            }
        }
    raise ValueError(f"Unsupported DB_ENGINE {engine!r}. Use sqlite or postgres.")


def https_settings(enabled):
    """Hardening for a site served over HTTPS behind a reverse proxy (DJANGO_HTTPS=True)."""
    if not enabled:
        return {}
    return {
        "SECURE_PROXY_SSL_HEADER": ("HTTP_X_FORWARDED_PROTO", "https"),
        "SECURE_SSL_REDIRECT": env_bool("DJANGO_SECURE_SSL_REDIRECT", True),
        "SESSION_COOKIE_SECURE": True,
        "CSRF_COOKIE_SECURE": True,
        "SECURE_HSTS_SECONDS": int(os.environ.get("DJANGO_HSTS_SECONDS", "3600")),
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", False),
        "SECURE_HSTS_PRELOAD": False,
        "SECURE_REFERRER_POLICY": "strict-origin-when-cross-origin",
        "SECURE_CONTENT_TYPE_NOSNIFF": True,
        # The health probes must answer over plain HTTP inside the private network.
        "SECURE_REDIRECT_EXEMPT": [r"^api/health/"],
    }
