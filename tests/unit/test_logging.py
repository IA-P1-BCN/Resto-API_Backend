"""Logging en texto/JSON y filtro de secretos (R-04 / HU-11)."""

import json
import logging

from app.core.logging import (
    REDACTED,
    JsonFormatter,
    RedactSecretsFilter,
    TextFormatter,
    redact_text,
    setup_logging,
)


def _record(msg: str, **extra) -> logging.LogRecord:
    record = logging.makeLogRecord(
        {"name": "test", "levelname": "INFO", "msg": msg})
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_redact_text_hides_key_value_secrets():
    text = redact_text("login password=Secreta123 token: abc.def")
    assert "Secreta123" not in text
    assert "abc.def" not in text
    assert f"password={REDACTED}" in text


def test_redact_text_hides_bearer_tokens():
    text = redact_text("Authorization: Bearer eyJhbGc.x.y")
    assert "eyJhbGc" not in text


def test_redact_text_hides_password_in_database_url():
    text = redact_text("postgresql+psycopg://user:supersecret@host/db")
    assert text == f"postgresql+psycopg://user:{REDACTED}@host/db"


def test_redact_text_keeps_normal_text():
    assert redact_text("Dish 7 created") == "Dish 7 created"


def test_filter_redacts_sensitive_extra_fields():
    record = _record(
        "user data", user={"email": "a@b.c", "password": "x"}, access_token="zzz"
    )
    RedactSecretsFilter().filter(record)
    assert record.user == {"email": "a@b.c", "password": REDACTED}
    assert record.access_token == REDACTED


def test_json_formatter_outputs_one_json_object():
    line = JsonFormatter().format(_record("Dish created", dish_id=7))
    data = json.loads(line)
    assert data["message"] == "Dish created"
    assert data["level"] == "INFO"
    assert data["dish_id"] == 7


def test_text_formatter_puts_extra_fields_on_the_same_line():
    line = TextFormatter().format(_record("Dish created", dish_id=7))
    assert line.endswith("test: Dish created dish_id=7")


def test_setup_logging_uses_json_in_production():
    try:
        setup_logging("production", "INFO")
        handler = logging.getLogger().handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)
        setup_logging("development", "INFO")
        handler = logging.getLogger().handlers[0]
        assert isinstance(handler.formatter, TextFormatter)
    finally:
        setup_logging()
