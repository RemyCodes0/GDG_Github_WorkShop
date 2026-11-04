"""Django settings for AUB Collab."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "abuse",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# Abuse prevention: rate limits on every API request plus tighter limits on sensitive
# actions. See abuse/throttles.py. Each rate can be overridden with an environment variable,
# for example THROTTLE_AUTH=10/min. THROTTLING_ENABLED=False turns all limits off (load tests).
def _rate(name, default):
    return os.environ.get(f"THROTTLE_{name.upper()}", default)


THROTTLING_ENABLED = os.environ.get("THROTTLING_ENABLED", "True") == "True"

REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "abuse.throttles.AnonBurstThrottle",
        "abuse.throttles.AnonSustainedThrottle",
        "abuse.throttles.UserBurstThrottle",
        "abuse.throttles.UserSustainedThrottle",
    ]
    if THROTTLING_ENABLED
    else [],
    "DEFAULT_THROTTLE_RATES": {
        "anon_burst": _rate("anon_burst", "30/min"),
        "anon_sustained": _rate("anon_sustained", "1000/day"),
        "user_burst": _rate("user_burst", "120/min"),
        "user_sustained": _rate("user_sustained", "10000/day"),
        # Sensitive actions, used with abuse.throttles.SensitiveActionThrottle
        "auth": _rate("auth", "5/min"),
        "applications": _rate("applications", "20/hour"),
        "project_create": _rate("project_create", "10/hour"),
    },
    # Behind a load balancer or reverse proxy, set this to the number of proxies so limits
    # use the real client IP from X-Forwarded-For instead of the proxy's address.
    "NUM_PROXIES": int(os.environ["NUM_PROXIES"]) if os.environ.get("NUM_PROXIES") else None,
    "EXCEPTION_HANDLER": "abuse.handlers.api_exception_handler",
}

# Reject oversized request bodies before they reach a view (CV uploads use file storage).
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get("MAX_REQUEST_BODY_BYTES", str(2 * 1024 * 1024)))
DATA_UPLOAD_MAX_NUMBER_FIELDS = 500
