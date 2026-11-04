"""Logging helpers: a filter that stamps every record with the request ID, and a JSON formatter.

JSON logs are one object per line, which log tools (Grafana Loki, Datadog, CloudWatch,
the ELK stack) can index without custom parsing.
"""
import json
import logging
from datetime import datetime, timezone

from .context import get_request_id

# Attributes every LogRecord has. Anything else was passed with extra={...} and is
# copied into the JSON output.
_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
    "request_id",
}


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)
