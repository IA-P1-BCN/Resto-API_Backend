"""Tests unitarios de la lógica de reservas (HU-10) y de send_email."""

import logging
from datetime import datetime

import pytest

from app.config import settings
from app.models.dining_table import DiningTable
from app.models.model_user import Role
from app.models.reservation import Reservation
from app.services import notifications
from app.services.reservations import find_overlapping


def _at(hour: int, minute: int) -> datetime:
    """Hora del 10/10/2026 sin zona horaria (reserved_at es TIMESTAMP sin zona)."""
    return datetime.fromisoformat(f"2026-10-10T{hour:02d}:{minute:02d}")


@pytest.fixture
def booked(db, make_user) -> Reservation:
    """Mesa con una reserva confirmada de 20:00 a 21:30."""
    user = make_user(Role.customer)
    table = DiningTable(number=1, capacity=4, location="indoor")
    db.add(table)
    db.flush()
    reservation = Reservation(
        user_id=user.id,
        table_id=table.id,
        reserved_at=_at(20, 0),
        duration_min=90,
        party_size=2,
    )
    db.add(reservation)
    db.commit()
    return reservation


@pytest.mark.parametrize(
    ("start", "duration", "overlaps"),
    [
        ((19, 0), 60, False),  # termina justo cuando empieza la otra
        ((19, 0), 61, True),
        ((20, 0), 90, True),  # mismo intervalo
        ((20, 30), 15, True),  # contenida
        ((19, 0), 180, True),  # la contiene
        ((21, 29), 60, True),
        ((21, 30), 60, False),  # empieza justo cuando termina la otra
    ],
)
def test_find_overlapping_uses_half_open_intervals(
    db, booked, start, duration, overlaps
):
    clash = find_overlapping(
        db,
        table_id=booked.table_id,
        reserved_at=_at(*start),
        duration_min=duration,
    )

    assert (clash is not None) is overlaps
    if overlaps:
        assert clash.id == booked.id


def test_find_overlapping_ignores_cancelled_and_excluded(db, booked):
    window = {
        "table_id": booked.table_id,
        "reserved_at": booked.reserved_at,
        "duration_min": 30,
    }

    assert find_overlapping(db, **window, exclude_id=booked.id) is None

    booked.status = "cancelled"
    db.commit()
    assert find_overlapping(db, **window) is None


def test_find_overlapping_ignores_other_tables(db, booked):
    assert (
        find_overlapping(
            db,
            table_id=booked.table_id + 1,
            reserved_at=booked.reserved_at,
            duration_min=90,
        )
        is None
    )


def test_send_email_disabled_only_logs(monkeypatch, caplog):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)

    with caplog.at_level(logging.INFO, logger=notifications.__name__):
        notifications.send_email("a@test.com", "Asunto", "<p>Hola</p>")

    assert "Email simulado" in caplog.text
    assert "a@test.com" in caplog.text


def test_send_email_enabled_does_not_raise(monkeypatch, caplog):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)

    with caplog.at_level(logging.WARNING, logger=notifications.__name__):
        notifications.send_email("a@test.com", "Asunto", "<p>Hola</p>")

    assert "HU-19" in caplog.text
