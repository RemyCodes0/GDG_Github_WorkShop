"""Upload checks. A file is accepted only if its size, extension AND actual content agree.

The extension and the browser's Content-Type are chosen by whoever uploads, so neither is
trusted on its own: the first bytes of the file must match the claimed type. A renamed
executable or HTML page is rejected even if it is called cv.pdf.
"""
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

# extension -> (content type served back, check on the file's first bytes)
FILE_TYPES = {
    "pdf": ("application/pdf", lambda head: head.startswith(b"%PDF-")),
    "png": ("image/png", lambda head: head.startswith(b"\x89PNG\r\n\x1a\n")),
    "jpg": ("image/jpeg", lambda head: head.startswith(b"\xff\xd8\xff")),
    "jpeg": ("image/jpeg", lambda head: head.startswith(b"\xff\xd8\xff")),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        lambda head: head.startswith(b"PK\x03\x04"),
    ),
}


def _is_real_docx(upload):
    """A .docx is a zip file; check it really contains a Word document."""
    upload.seek(0)
    try:
        with zipfile.ZipFile(upload) as archive:
            return "word/document.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False
    finally:
        upload.seek(0)


def validate_upload(upload, allowed=None):
    """Return (extension, content_type) for a valid upload, or raise ValidationError."""
    allowed = allowed or settings.FILE_UPLOAD_ALLOWED_TYPES
    max_bytes = settings.FILE_UPLOAD_MAX_BYTES

    if upload.size == 0:
        raise ValidationError("The file is empty.", code="empty")
    if upload.size > max_bytes:
        raise ValidationError(
            f"The file is too large. The limit is {max_bytes // (1024 * 1024)} MB.", code="too_large"
        )

    extension = Path(upload.name).suffix.lower().lstrip(".")
    if extension not in allowed or extension not in FILE_TYPES:
        raise ValidationError(
            f"This file type is not allowed. Use one of: {', '.join(sorted(allowed))}.", code="type"
        )

    upload.seek(0)
    head = upload.read(16)
    upload.seek(0)
    content_type, matches = FILE_TYPES[extension]
    if not matches(head) or (extension == "docx" and not _is_real_docx(upload)):
        raise ValidationError("The file's contents do not match its extension.", code="content")

    return extension, content_type
