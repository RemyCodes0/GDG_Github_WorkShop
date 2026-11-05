# AUB Collab API image: Django served by Gunicorn, static files by WhiteNoise.
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so code changes do not reinstall packages.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Build time only values: collectstatic needs settings to import, not real secrets.
RUN DJANGO_SECRET_KEY=build-only DJANGO_DEBUG=False DJANGO_STATIC_MANIFEST=True \
    python manage.py collectstatic --noinput

# Never run the app as root.
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

ENV DJANGO_DEBUG=False \
    DJANGO_STATIC_MANIFEST=True \
    PORT=8000 \
    GUNICORN_WORKERS=3

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health/', timeout=4).status == 200 else 1)"

# Migrations run once per start; Gunicorn then serves with several worker processes.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS} --timeout 30 --access-logfile - --forwarded-allow-ips='*'"]
