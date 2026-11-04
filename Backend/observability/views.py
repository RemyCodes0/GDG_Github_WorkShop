"""Liveness and readiness probes, the two checks hosting platforms and Kubernetes expect.

/api/health/live/   the process is up and can answer. Never touches the database, so a slow
                    database does not get the server restarted for no reason.
/api/health/ready/  the server can do real work: every dependency answered. Returns 503
                    otherwise, so a load balancer stops sending it traffic until it recovers.
"""
import logging
import time

from django.db import connections
from django.http import JsonResponse

from .context import get_request_id

logger = logging.getLogger("aubcollab.health")


def _check_databases():
    results = {}
    for alias in connections:
        start = time.perf_counter()
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            results[f"database:{alias}"] = {
                "status": "ok",
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
            }
        except Exception as exc:  # any failure means "not ready", never a 500
            logger.error("Readiness check failed for database %s", alias, exc_info=True)
            results[f"database:{alias}"] = {"status": "error", "error": exc.__class__.__name__}
    return results


def liveness(_request):
    return JsonResponse({"status": "ok"})


def readiness(_request):
    checks = _check_databases()
    ready = all(check["status"] == "ok" for check in checks.values())
    return JsonResponse(
        {"status": "ok" if ready else "unavailable", "checks": checks, "request_id": get_request_id()},
        status=200 if ready else 503,
    )
