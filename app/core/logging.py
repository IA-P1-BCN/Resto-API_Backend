"""Logging configuration for the whole API (R-04 / HU-11).

- Local (ENVIRONMENT != "production"): readable text logs.
- Production: one JSON object per line, easy to search in Render.
- A filter hides secrets (passwords, tokens, keys, DB credentials) before
  any log is written.

Usage in any module:
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Dish created", extra={"dish_id": dish.id})
"""

import json
import logging
import re
from datetime import UTC, datetime

from app.config import settings

REDACTED = "***"

# Field names whose value must never appear in a log.
SENSITIVE_KEYS = (
    "password",
    "token",
    "secret",
    "authorization",
    "api_key",
    "apikey",
)

# Patterns inside free text: "password=abc", "Bearer abc", "user:pass@host".
_KEY_VALUE_RE = re.compile(
    r"(?i)\b(\w*(?:"
    + "|".join(SENSITIVE_KEYS)
    + r")\w*)(\s*[=:]\s*)(['\"]?)(?:bearer\s+)?[^\s,'\"}]+"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[\w\-.~+/]+=*")
_URL_CREDENTIALS_RE = re.compile(r"(://[^:/\s@]+:)[^@\s]+@")

# Attributes every LogRecord has; anything else came from extra={...}.
# "color_message" is a duplicate that uvicorn adds for coloured terminals.
_STANDARD_ATTRS = set(vars(logging.makeLogRecord({}))) | {
    "message",
    "asctime",
    "color_message",
}


def redact_text(text: str) -> str:
    """Hide secrets that appear inside a text."""
    text = _KEY_VALUE_RE.sub(
        lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}{REDACTED}", text
    )
    text = _BEARER_RE.sub(f"Bearer {REDACTED}", text)
    return _URL_CREDENTIALS_RE.sub(rf"\1{REDACTED}@", text)


def _is_sensitive(key: str) -> bool:
    key = key.lower()
    return any(word in key for word in SENSITIVE_KEYS)


def _redact_value(key: str, value: object) -> object:
    if _is_sensitive(key):
        return REDACTED
    if isinstance(value, dict):
        return {k: _redact_value(str(k), v) for k, v in value.items()}
    if isinstance(value, str):
        return redact_text(value)
    return value


class RedactSecretsFilter(logging.Filter):
    """Clean the message and the extra fields of every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = None
        for key, value in list(vars(record).items()):
            if key not in _STANDARD_ATTRS:
                setattr(record, key, _redact_value(key, value))
        return True


def _extra_fields(record: logging.LogRecord) -> dict:
    return {k: v for k, v in vars(record).items() if k not in _STANDARD_ATTRS}


class JsonFormatter(logging.Formatter):
    """One JSON object per line (production)."""

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **_extra_fields(record),
        }
        if record.exc_info:
            data["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(data, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """Readable line for the terminal (local), extra fields at the end."""

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        extra = _extra_fields(record)
        if extra:
            line += " " + " ".join(f"{k}={v}" for k, v in extra.items())
        return line

    def formatException(self, ei) -> str:
        return redact_text(super().formatException(ei))


def setup_logging(environment: str | None = None, level: str | None = None) -> None:
    """Configure the root logger. Call it once, when the app starts."""
    environment = (environment or settings.ENVIRONMENT).lower()
    level = (level or settings.LOG_LEVEL).upper()

    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter() if environment == "production" else TextFormatter()
    )
    handler.addFilter(RedactSecretsFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Uvicorn logs go through the same handler so they share the format.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True