from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .base import VersionedAPIView
from .versioning import allowed_versions, deprecated_versions, latest_version


class ApiRootView(APIView):
    """GET /api/  Lists the API versions so clients can discover what is supported."""

    permission_classes = [AllowAny]
    versioning_class = None

    def get(self, request):
        deprecated = deprecated_versions()
        versions = []
        for version in allowed_versions():
            entry = {
                "version": version,
                "url": request.build_absolute_uri(f"/api/{version}/"),
                "status": "deprecated" if version in deprecated else "supported",
            }
            sunset = deprecated.get(version, {}).get("sunset") if version in deprecated else None
            if sunset:
                entry["sunset"] = str(sunset)
            versions.append(entry)
        return Response({"latest": latest_version(), "versions": versions})


class HealthView(VersionedAPIView):
    """GET /api/<version>/health/  Confirms the API is running."""

    permission_classes = [AllowAny]

    def get(self, request, version=None):
        return Response({"status": "ok", "version": request.version})


class UnknownVersionView(VersionedAPIView):
    """Catches /api/v<N>/... paths that no versioned route matched.

    For a version that does not exist, the version check rejects the request first and the
    404 says so. For a real version with an unknown path, it is a plain JSON 404.
    Both apply to every HTTP method.
    """

    permission_classes = [AllowAny]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        raise NotFound()
