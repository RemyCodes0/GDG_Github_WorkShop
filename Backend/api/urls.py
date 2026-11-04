"""Entry point for the API: /api/ lists versions, /api/<version>/ routes to that version.

To add version 2:
  1. create api/v2/urls.py (start by copying v1 and changing what differs)
  2. add "v2" to REST_FRAMEWORK["ALLOWED_VERSIONS"] in config/settings.py
  3. add it to VERSION_URLCONFS below
  4. when v1 should be retired, list it in API_DEPRECATED_VERSIONS with a sunset date
"""
from django.urls import include, path, re_path

from .views import ApiRootView, UnknownVersionView

VERSION_URLCONFS = {
    "v1": "api.v1.urls",
}

urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
]

for _version, _urlconf in VERSION_URLCONFS.items():
    urlpatterns.append(
        re_path(rf"^(?P<version>{_version})/", include((_urlconf, _version), namespace=_version))
    )

# Any other vN prefix gets a clear JSON 404 instead of a generic Django error page.
urlpatterns.append(re_path(r"^(?P<version>v[0-9]+)/", UnknownVersionView.as_view()))
