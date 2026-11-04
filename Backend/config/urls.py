"""URL configuration for AUB Collab."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    # Unversioned health check kept for existing scripts. New code should use /api/v1/health/.
    path("api/health/", health),
    path("api/", include("api.urls")),
]
