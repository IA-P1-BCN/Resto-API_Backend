"""Unit tests for dining_table_service (HU-09).

Assumptions: see PENDING-CONTRACTS.md (E1).
"""

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

# ASSUMPTION E1: NotFoundError/ConflictError exponen el atributo `code`.
from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.dining_table import (
    DiningTableCreate,
    DiningTableUpdate,
)
from app.services import dining_table_service as service


def _create(db: Session, number: int = 1, capacity: int = 4, location: str = "indoor"):
    return service.create_table(
        db, DiningTableCreate(number=number, capacity=capacity, location=location)
    )


# DiningTableUpdate es un reemplazo completo: exige number, capacity, location y status.
def _update_payload(
    number: int = 1,
    capacity: int = 6,
    location: str = "terrace",
    status: str = "reserved",
) -> DiningTableUpdate:
    return DiningTableUpdate(
        number=number, capacity=capacity, location=location, status=status
    )


# --- create ----------------------------------------------------------------------------------


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


# --- get -------------------------------------------------------------------------------------


def test_get_table_ok(db: Session) -> None:
    created = _create(db, number=7)

    table = service.get_table(db, created.id)

    assert table.id == created.id
    assert table.number == 7


def test_get_table_not_found(db: Session) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        service.get_table(db, 9999)

    assert exc_info.value.code == "not_found"


# --- list ------------------------------------------------------------------------------------


def test_list_tables_empty(db: Session) -> None:
    assert service.list_tables(db) == ([], 0)


def test_list_tables_pagination(db: Session) -> None:
    for number in range(1, 6):
        _create(db, number=number)

    items, total = service.list_tables(db, skip=1, limit=2)

    assert len(items) == 2
    assert total == 5


def test_list_tables_ordered_by_id(db: Session) -> None:
    # Se crean con number desordenado para que el orden no coincida por casualidad.
    created = [_create(db, number=number) for number in (3, 1, 2)]

    items, _ = service.list_tables(db)

    ids = [item.id for item in items]
    assert ids == sorted(ids)
    assert ids == [table.id for table in created]


# --- update ----------------------------------------------------------------------------------


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


# --- change_status ---------------------------------------------------------------------------


def test_change_status_ok(db: Session) -> None:
    created = _create(db)

    table = service.change_status(db, created.id, "occupied")

    assert table.status == "occupied"
    assert service.get_table(db, created.id).status == "occupied"


def test_change_status_not_found(db: Session) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        service.change_status(db, 9999, "occupied")

    assert exc_info.value.code == "not_found"


# --- delete ----------------------------------------------------------------------------------


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
