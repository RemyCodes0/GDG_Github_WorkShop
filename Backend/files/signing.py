"""Short lived, tamper proof download links.

A link carries the file ID and the ID of the user it was issued to, signed with SECRET_KEY
and timestamped. Changing any character breaks the signature, and the link stops working
after FILE_LINK_MAX_AGE seconds, so a forwarded or leaked link expires on its own.
"""
from django.conf import settings
from django.core import signing

SALT = "aubcollab.files.download"


def make_token(stored_file, user):
    return signing.dumps({"f": str(stored_file.pk), "u": user.pk}, salt=SALT, compress=True)


def read_token(token, max_age=None):
    """Return (file_id, user_id). Raises signing.SignatureExpired or signing.BadSignature."""
    data = signing.loads(token, salt=SALT, max_age=max_age or settings.FILE_LINK_MAX_AGE)
    return data["f"], data["u"]
