"""URL configuration for AUB Collab."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

from observability.views import liveness, readiness


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/health/live/", liveness, name="health-live"),
    path("api/health/ready/", readiness, name="health-ready"),
]
