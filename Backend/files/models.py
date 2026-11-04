import hashlib
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models


def private_storage():
    """Files live outside MEDIA_ROOT and have no public URL; they are only served through a
    short lived signed link, after the app checks who is asking. A function, so migrations
    do not hard code the folder."""
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT, base_url=None)


def _random_path(instance, filename):
    # The stored name never contains the user's file name, so it cannot be guessed or abused.
    return f"{instance.pk.hex[:2]}/{instance.pk.hex}.{instance.extension}"


class StoredFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(storage=private_storage, upload_to=_random_path, max_length=200)
    original_name = models.CharField(max_length=255)
    extension = models.CharField(max_length=10)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64, help_text="Detects tampering and duplicate uploads")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_name} ({self.owner})"

    @staticmethod
    def checksum(upload):
        digest = hashlib.sha256()
        upload.seek(0)
        for chunk in upload.chunks():
            digest.update(chunk)
        upload.seek(0)
        return digest.hexdigest()

    def delete(self, *args, **kwargs):
        storage, name = self.file.storage, self.file.name
        result = super().delete(*args, **kwargs)
        if name:
            storage.delete(name)  # remove the file from disk, not just the database row
        return result
