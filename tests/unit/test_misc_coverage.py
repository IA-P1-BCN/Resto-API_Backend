"""Tests unitarios de detalles sueltos: __repr__ de modelos, SQL de fin de reserva
en PostgreSQL, email de cancelación sin destinatario y logs JSON con excepción."""

import json
import logging
import sys
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.core.logging import JsonFormatter
from app.models.dining_table import DiningTable
from app.models.reservation import Reservation
from app.services import reservations as service


def test_dining_table_repr():
    table = DiningTable(id=3, number=7, capacity=4, location="indoor", status="available")

    assert repr(table) == "<DiningTable id=3 number=7 status=available>"


def test_reservation_repr_includes_table_and_time():
    reservation = Reservation(
        id=5, user_id=1, table_id=3, reserved_at=datetime.fromisoformat("2026-10-10T20:00"),
        duration_min=90, party_size=2, status="confirmed",
    )

    text = repr(reservation)

    assert text.startswith("<Reservation id=5 table_id=3 ")
    assert "2026-10-10" in text


def test_reservation_end_compiles_to_make_interval_in_postgres():
    stmt = select(service.reservation_end(Reservation.reserved_at, Reservation.duration_min))

    sql = str(stmt.compile(dialect=postgresql.dialect()))

    assert "make_interval(mins => reservations.duration_min)" in sql
    assert "reservations.reserved_at +" in sql


def test_cancellation_email_without_user_returns_none(db):
    reservation = Reservation(
        user_id=999_999, table_id=1, reserved_at=datetime.fromisoformat("2026-10-10T20:00"),
        duration_min=90, party_size=2,
    )

    assert service.cancellation_email(db, reservation) is None


def test_json_formatter_includes_redacted_exception():
    try:
        raise ValueError("fallo con password=supersecreta")
    except ValueError:
        exc_info = sys.exc_info()
    record = logging.makeLogRecord(
        {"name": "test", "levelname": "ERROR", "msg": "boom", "exc_info": exc_info}
    )

    data = json.loads(JsonFormatter().format(record))

    assert data["message"] == "boom"
    assert "ValueError" in data["exception"]
    assert "supersecreta" not in data["exception"]
