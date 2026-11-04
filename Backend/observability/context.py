"""Per-request context shared with logging.

The request ID lives in a ContextVar, so it is correct per request under both WSGI threads
and ASGI async code, and any log line written while handling a request can include it.
"""
import re
import uuid
from contextvars import ContextVar

REQUEST_ID_HEADER = "X-Request-ID"

# Accept IDs from a proxy or the frontend only if they look safe to echo back and log.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def new_request_id() -> str:
    return uuid.uuid4().hex


def clean_request_id(value: str | None) -> str:
    """Reuse an incoming ID when it is well formed, otherwise make a new one."""
    if value and _VALID_REQUEST_ID.match(value):
        return value
    return new_request_id()


def get_request_id() -> str | None:
    return _request_id.get()


def set_request_id(value: str | None):
    return _request_id.set(value)


def reset_request_id(token) -> None:
    _request_id.reset(token)
