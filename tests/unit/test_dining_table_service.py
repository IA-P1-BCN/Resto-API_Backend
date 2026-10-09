"""Unit tests for dining_table_service (HU-09).

Assumptions: see PENDING-CONTRACTS.md (E1).
"""

from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.reservation import Reservation
from app.schemas.dining_table import (
    DiningTableCreate,
    DiningTableUpdate,
)
from app.services import dining_table_service as service


def _create(db: Session, number: int = 1, capacity: int = 4, location: str = "indoor"):
    return service.create_table(
        db, DiningTableCreate(number=number, capacity=capacity, location=location)
    )


def _update_payload(
    number: int = 1,
    capacity: int = 6,
    location: str = "terrace",
    status: str = "reserved",
) -> DiningTableUpdate:
    return DiningTableUpdate(
        number=number, capacity=capacity, location=location, status=status
    )


def test_create_table_ok(db: Session) -> None:
    table = _create(db, number=1, capacity=4, location="indoor")

    assert table.id is not None
    assert (table.number, table.capacity, table.location) == (1, 4, "indoor")
    assert table.status == "available"
    _, total = service.list_tables(db)
    assert total == 1


def test_create_table_number_already_taken(db: Session) -> None:
    _create(db, number=1)

    with pytest.raises(ConflictError) as exc_info:
        _create(db, number=1, capacity=2, location="bar")

    assert exc_info.value.code == "conflict"


def test_create_table_capacity_zero_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        DiningTableCreate(number=1, capacity=0, location="indoor")


def test_get_table_ok(db: Session) -> None:
    created = _create(db, number=7)

    table = service.get_table(db, created.id)

    assert table.id == created.id
    assert table.number == 7


def test_get_table_not_found(db: Session) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        service.get_table(db, 9999)

    assert exc_info.value.code == "not_found"


def test_list_tables_empty(db: Session) -> None:
    assert service.list_tables(db) == ([], 0)


def test_list_tables_pagination(db: Session) -> None:
    for number in range(1, 6):
        _create(db, number=number)

    items, total = service.list_tables(db, skip=1, limit=2)

    assert len(items) == 2
    assert total == 5


def test_list_tables_ordered_by_id(db: Session) -> None:
    created = [_create(db, number=number) for number in (3, 1, 2)]

    items, _ = service.list_tables(db)

    ids = [item.id for item in items]
    assert ids == sorted(ids)
    assert ids == [table.id for table in created]


def test_update_table_ok(db: Session) -> None:
    created = _create(db, number=1, capacity=4, location="indoor")

    updated = service.update_table(
        db,
        created.id,
        _update_payload(number=2, capacity=6, location="terrace", status="reserved"),
    )

    assert updated.id == created.id
    assert (updated.number, updated.capacity, updated.location, updated.status) == (
        2,
        6,
        "terrace",
        "reserved",
    )


def test_update_table_number_conflict(db: Session) -> None:
    _create(db, number=1)
    other = _create(db, number=2)

    with pytest.raises(ConflictError) as exc_info:
        service.update_table(db, other.id, _update_payload(number=1))

    assert exc_info.value.code == "conflict"


def test_update_table_same_number_ok(db: Session) -> None:
    created = _create(db, number=1, capacity=4)

    updated = service.update_table(
        db, created.id, _update_payload(number=1, capacity=8)
    )

    assert updated.number == 1
    assert updated.capacity == 8


def test_update_table_not_found(db: Session) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        service.update_table(db, 9999, _update_payload())

    assert exc_info.value.code == "not_found"


def test_change_status_ok(db: Session) -> None:
    created = _create(db)

    table = service.change_status(db, created.id, "occupied")

    assert table.status == "occupied"
    assert service.get_table(db, created.id).status == "occupied"


def test_change_status_not_found(db: Session) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        service.change_status(db, 9999, "occupied")

    assert exc_info.value.code == "not_found"


def test_delete_table_ok(db: Session) -> None:
    created = _create(db)
    table_id = created.id

    service.delete_table(db, table_id)

    with pytest.raises(NotFoundError):
        service.get_table(db, table_id)


def test_delete_table_not_found(db: Session) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        service.delete_table(db, 9999)

    assert exc_info.value.code == "not_found"


def _at(hour: int, minute: int = 0) -> datetime:
    """10/10/2026 at the given time, without time zone (like reserved_at)."""
    return datetime.fromisoformat(f"2026-10-10T{hour:02d}:{minute:02d}")


def _reserve(
    db: Session,
    user_id: int,
    table_id: int,
    start: datetime,
    duration_min: int = 90,
    status: str = "confirmed",
) -> Reservation:
    reservation = Reservation(
        user_id=user_id,
        table_id=table_id,
        reserved_at=start,
        duration_min=duration_min,
        party_size=2,
        status=status,
    )
    db.add(reservation)
    db.flush()
    return reservation


def _available_numbers(db: Session, **kwargs) -> list[int]:
    items, total = service.list_available_tables(db, **kwargs)
    assert total == len(items)
    return [table.number for table in items]


def test_available_tables_filters_by_capacity_and_orders_by_best_fit(
    db: Session,
) -> None:
    _create(db, number=1, capacity=6)
    _create(db, number=2, capacity=2)
    _create(db, number=3, capacity=4)
    _create(db, number=4, capacity=4)

    numbers = _available_numbers(db, reserved_at=_at(20), party_size=3)

    assert numbers == [3, 4, 1]


def test_available_tables_excludes_out_of_service(db: Session) -> None:
    _create(db, number=1)
    broken = _create(db, number=2)
    service.change_status(db, broken.id, "out_of_service")

    assert _available_numbers(db, reserved_at=_at(20), party_size=2) == [1]


@pytest.mark.parametrize(
    ("start", "duration", "available"),
    [
        ((18, 30), 90, True),
        ((18, 31), 90, False),
        ((20, 30), 30, False),
        ((19, 0), 180, False),
        ((21, 29), 60, False),
        ((21, 30), 60, True),
    ],
)
def test_available_tables_uses_half_open_intervals(
    db: Session, make_user, start, duration, available
) -> None:
    table = _create(db, number=1)
    _reserve(db, make_user("customer").id, table.id, _at(20), duration_min=90)

    numbers = _available_numbers(
        db, reserved_at=_at(*start), party_size=2, duration_min=duration
    )

    assert numbers == ([1] if available else [])


def test_available_tables_ignores_cancelled_reservations(
    db: Session, make_user
) -> None:
    table = _create(db, number=1)
    _reserve(db, make_user("customer").id, table.id, _at(20), status="cancelled")

    assert _available_numbers(db, reserved_at=_at(20), party_size=2) == [1]


def test_available_tables_only_excludes_the_booked_table(
    db: Session, make_user
) -> None:
    booked = _create(db, number=1)
    _create(db, number=2)
    _reserve(db, make_user("customer").id, booked.id, _at(20))

    assert _available_numbers(db, reserved_at=_at(20, 30), party_size=2) == [2]


def test_available_tables_converts_aware_datetime_to_utc(
    db: Session, make_user
) -> None:
    table = _create(db, number=1)
    _reserve(db, make_user("customer").id, table.id, _at(20))
    madrid = datetime.fromisoformat("2026-10-10T22:00:00+02:00")

    assert _available_numbers(db, reserved_at=madrid, party_size=2) == []


def test_available_tables_paginates(db: Session) -> None:
    for number in range(1, 6):
        _create(db, number=number)

    items, total = service.list_available_tables(
        db, reserved_at=_at(20), party_size=2, skip=2, limit=2
    )

    assert total == 5
    assert [table.number for table in items] == [3, 4]
