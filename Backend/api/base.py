"""Base view for every versioned endpoint. Adds the version headers to each response."""
from rest_framework.views import APIView

from .versioning import AUBCollabVersioning, http_date, deprecated_versions, latest_version


class VersionedAPIView(APIView):
    versioning_class = AUBCollabVersioning

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        version = getattr(request, "version", None)
        if not version:
            return response

        response["API-Version"] = version
        deprecation = deprecated_versions().get(version)
        if deprecation is not None:
            response["Deprecation"] = "true"
            sunset = deprecation.get("sunset") if isinstance(deprecation, dict) else None
            if sunset:
                response["Sunset"] = http_date(sunset)
            newest = latest_version()
            if newest and newest != version:
                response["Link"] = f'</api/{newest}/>; rel="successor-version"'
        return response
