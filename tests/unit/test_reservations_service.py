"""Tests unitarios de la lógica de reservas (HU-10) y de send_email."""

import logging
from datetime import datetime

import pytest

from app.config import settings
from app.core.exceptions import ReservationConflict, UnprocessableError
from app.models.dining_table import DiningTable
from app.models.reservation import Reservation
from app.schemas.reservation import ReservationUpdate
from app.services import notifications
from app.services import reservations as service
from app.services.reservations import find_overlapping


def _at(hour: int, minute: int) -> datetime:
    """Hora del 10/10/2026 sin zona horaria (reserved_at es TIMESTAMP sin zona)."""
    return datetime.fromisoformat(f"2026-10-10T{hour:02d}:{minute:02d}")


@pytest.fixture
def booked(db, make_user) -> Reservation:
    """Mesa con una reserva confirmada de 20:00 a 21:30."""
    user = make_user("customer")
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


def test_send_email_never_raises(monkeypatch, caplog):
    def broken_info(*args, **kwargs):
        raise RuntimeError("fallo del logger")

    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)
    monkeypatch.setattr(notifications.logger, "info", broken_info)

    with caplog.at_level(logging.ERROR, logger=notifications.__name__):
        notifications.send_email("a@test.com", "Asunto", "<p>Hola</p>")

    assert "Error enviando email" in caplog.text


# --- _ensure_capacity ------------------------------------------------------------------


@pytest.mark.parametrize("party_size", [1, 4])
def test_ensure_capacity_accepts_up_to_capacity(party_size):
    service._ensure_capacity(DiningTable(number=1, capacity=4), party_size)


def test_ensure_capacity_rejects_over_capacity():
    with pytest.raises(UnprocessableError) as exc_info:
        service._ensure_capacity(DiningTable(number=1, capacity=4), 5)

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "party_size_exceeds_capacity"


# --- Reglas de update_reservation (sin BD) ---------------------------------------------


class FakeSession:
    """Lo mínimo de Session que usa update_reservation."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def refresh(self, instance: object) -> None:
        pass


@pytest.fixture
def checks(monkeypatch) -> dict:
    """Sustituye la carga de la mesa y la búsqueda de solapes por espías."""
    calls: dict = {"tables": [], "overlaps": [], "clash": None, "capacity": 4}

    def fake_table(db, table_id):
        calls["tables"].append(table_id)
        return DiningTable(id=table_id, number=table_id, capacity=calls["capacity"])

    def fake_overlapping(db, **kwargs):
        calls["overlaps"].append(kwargs)
        return calls["clash"]

    monkeypatch.setattr(service, "_get_table_for_update", fake_table)
    monkeypatch.setattr(service, "find_overlapping", fake_overlapping)
    return calls


def _reservation(status: str = "confirmed") -> Reservation:
    return Reservation(
        id=10,
        user_id=1,
        table_id=1,
        reserved_at=_at(20, 0),
        duration_min=90,
        party_size=2,
        status=status,
    )


def test_update_notes_skips_capacity_and_overlap(checks):
    db = FakeSession()

    service.update_reservation(db, _reservation(), ReservationUpdate(notes="Ventana"))

    assert checks["tables"] == []
    assert checks["overlaps"] == []
    assert db.committed


def test_update_party_size_checks_capacity_only(checks):
    service.update_reservation(
        FakeSession(), _reservation(), ReservationUpdate(party_size=3)
    )

    assert checks["tables"] == [1]
    assert checks["overlaps"] == []


def test_update_time_checks_overlap_excluding_itself(checks):
    reservation = _reservation()

    service.update_reservation(
        FakeSession(), reservation, ReservationUpdate(reserved_at=_at(21, 0))
    )

    assert checks["overlaps"] == [
        {
            "table_id": 1,
            "reserved_at": _at(21, 0),
            "duration_min": 90,
            "exclude_id": reservation.id,
        }
    ]
    assert reservation.reserved_at == _at(21, 0)


def test_update_table_checks_capacity_and_overlap_on_new_table(checks):
    service.update_reservation(
        FakeSession(), _reservation(), ReservationUpdate(table_id=2)
    )

    assert checks["tables"] == [2]
    assert checks["overlaps"][0]["table_id"] == 2


def test_update_status_of_active_reservation_skips_checks(checks):
    reservation = _reservation()

    service.update_reservation(
        FakeSession(), reservation, ReservationUpdate(status="no_show")
    )

    assert checks["tables"] == []
    assert checks["overlaps"] == []
    assert reservation.status == "no_show"


def test_reactivating_cancelled_reservation_checks_overlap(checks):
    service.update_reservation(
        FakeSession(), _reservation("cancelled"), ReservationUpdate(status="confirmed")
    )

    assert len(checks["overlaps"]) == 1


def test_update_with_overlap_raises_and_rolls_back(checks):
    checks["clash"] = Reservation(
        id=11, reserved_at=_at(20, 30), duration_min=60, table_id=1
    )
    reservation = _reservation()
    db = FakeSession()

    with pytest.raises(ReservationConflict):
        service.update_reservation(
            db, reservation, ReservationUpdate(reserved_at=_at(21, 0))
        )

    assert db.rolled_back and not db.committed
    assert reservation.reserved_at == _at(20, 0)


def test_update_over_capacity_raises_and_rolls_back(checks):
    checks["capacity"] = 2
    reservation = _reservation()
    db = FakeSession()

    with pytest.raises(UnprocessableError):
        service.update_reservation(db, reservation, ReservationUpdate(party_size=3))

    assert db.rolled_back and not db.committed
    assert reservation.party_size == 2
