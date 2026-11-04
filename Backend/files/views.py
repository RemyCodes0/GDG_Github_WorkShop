from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.urls import reverse
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import StoredFile
from .signing import make_token, read_token
from .validators import validate_upload


def _describe(request, stored):
    token = make_token(stored, request.user)
    return {
        "id": str(stored.pk),
        "name": stored.original_name,
        "content_type": stored.content_type,
        "size": stored.size,
        "sha256": stored.sha256,
        "download_url": request.build_absolute_uri(reverse("file-download", args=[token])),
    }


def can_access(user, stored):
    """Who may download a file. Today: its owner and staff. Later, for example, the owner of
    a project the file's owner applied to."""
    return user.is_authenticated and (stored.owner_id == user.pk or user.is_staff)


class UploadView(APIView):
    """POST /api/files/  multipart field "file". Returns the file's details and a download link."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": 'Send the file in a "file" form field.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            extension, content_type = validate_upload(upload)
        except ValidationError as exc:
            return Response({"detail": exc.messages[0], "code": exc.code}, status=status.HTTP_400_BAD_REQUEST)

        stored = StoredFile(
            owner=request.user,
            original_name=upload.name[:255],
            extension=extension,
            content_type=content_type,
            size=upload.size,
            sha256=StoredFile.checksum(upload),
        )
        with transaction.atomic():
            stored.file.save("upload", upload, save=False)
            stored.save()
        return Response(_describe(request, stored), status=status.HTTP_201_CREATED)


class FileDetailView(APIView):
    """GET /api/files/<id>/  details and a fresh link.  DELETE removes the file (owner only)."""

    permission_classes = [IsAuthenticated]

    def _get(self, request, file_id):
        stored = StoredFile.objects.filter(pk=file_id).first()
        # Same answer for "does not exist" and "not yours", so IDs cannot be probed.
        if stored is None or not can_access(request.user, stored):
            raise Http404
        return stored

    def get(self, request, file_id):
        return Response(_describe(request, self._get(request, file_id)))

    def delete(self, request, file_id):
        stored = self._get(request, file_id)
        if stored.owner_id != request.user.pk:
            raise Http404
        stored.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def download(request, token):
    """GET /api/files/download/<token>/  Serves the file if the link is valid and not expired.

    The link must be opened by the user it was issued to, while signed in.
    """
    try:
        file_id, user_id = read_token(token)
    except signing.SignatureExpired:
        return JsonResponse({"detail": "This link has expired. Request a new one."}, status=410)
    except signing.BadSignature:
        raise Http404

    stored = StoredFile.objects.filter(pk=file_id).first()
    if stored is None or request.user.pk != user_id or not can_access(request.user, stored):
        raise Http404

    response = FileResponse(
        stored.file.open("rb"),
        as_attachment=True,  # never rendered in the page, even if a browser guesses wrong
        filename=stored.original_name,
        content_type=stored.content_type,
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return response
