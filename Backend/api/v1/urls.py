"""Routes for version 1 of the API, mounted at /api/v1/.

New features add their routes here, for example:
    path("projects/", include("projects.urls")),
"""
from django.urls import path

from api.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
]
