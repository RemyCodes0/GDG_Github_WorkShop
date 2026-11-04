"""python manage.py cachecheck  Confirms the configured cache backend can write, read and delete."""
import time
import uuid

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Check that the configured cache backend works."

    def handle(self, *args, **options):
        backend = settings.CACHES["default"]["BACKEND"].rsplit(".", 1)[-1]
        key = f"cachecheck:{uuid.uuid4().hex}"
        start = time.perf_counter()
        try:
            cache.set(key, "ok", timeout=30)
            value = cache.get(key)
            cache.delete(key)
        except Exception as exc:
            raise CommandError(f"{backend}: cache is not reachable ({exc.__class__.__name__}: {exc})")

        duration_ms = (time.perf_counter() - start) * 1000
        if backend == "DummyCache":
            self.stdout.write(self.style.WARNING("DummyCache: caching is turned off (CACHE_URL=dummy://)"))
        elif value != "ok":
            raise CommandError(f"{backend}: wrote a value but could not read it back")
        else:
            self.stdout.write(self.style.SUCCESS(f"{backend}: OK ({duration_ms:.1f} ms round trip)"))
