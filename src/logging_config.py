"""Structured JSON logging with a privacy filter (guardrail GR-10).

Logs carry ids and aggregates only. The privacy filter redacts any extra field
whose name is a known personal-data field and any non-aggregate value
(DataFrame, Series, arrays, long sequences) that could leak row-level data.
"""

import json
import logging
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

REDACTED = "[REDACTED]"
MAX_SEQUENCE_LEN = 50

DEFAULT_PII_FIELDS: frozenset[str] = frozenset(
    {"member_id", "id", "url", "emp_title", "desc", "title", "zip_code", "name", "email"}
)

_RESERVED = frozenset(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}


def _is_row_level(value: Any) -> bool:
    """Return True if ``value`` looks like row-level data rather than an aggregate."""
    if hasattr(value, "shape") and getattr(value, "ndim", 0) >= 1:
        return True
    return isinstance(value, list | tuple | set) and len(value) > MAX_SEQUENCE_LEN


class PrivacyFilter(logging.Filter):
    """Redact personal-data fields and row-level values from log records."""

    def __init__(self, pii_fields: Iterable[str] = DEFAULT_PII_FIELDS) -> None:
        super().__init__()
        self.pii_fields = frozenset(f.lower() for f in pii_fields)

    def filter(self, record: logging.LogRecord) -> bool:
        """Mutate the record in place; never drops it."""
        for key in list(vars(record)):
            if key in _RESERVED:
                continue
            value = getattr(record, key)
            if key.lower() in self.pii_fields or _is_row_level(value):
                setattr(record, key, REDACTED)
        return True


class JsonFormatter(logging.Formatter):
    """Render each record as one JSON line including ``extra`` fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize the record to JSON."""
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload |= {k: v for k, v in vars(record).items() if k not in _RESERVED}
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON handler with the privacy filter on the root logger.

    Args:
        level: Root logging level name.
    """
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(PrivacyFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
