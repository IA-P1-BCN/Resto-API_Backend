"""
Business logic for dining tables (HU-09).

Assumptions: see PENDING-CONTRACTS.md (E1 for exceptions, P1 for
pagination).
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.dining_table import DiningTable
from app.models.model_order import Order
from app.models.reservation import DEFAULT_DURATION_MIN, Reservation
from app.schemas.dining_table import DiningTableCreate, DiningTableUpdate
from app.services.reservations import CANCELLED, reservation_end

logger = logging.getLogger(__name__)

CONFLICT_CODE = "conflict"
TABLE_IN_USE_CODE = "table_in_use"
NOT_FOUND_CODE = "not_found"
OUT_OF_SERVICE = "out_of_service"

def _ensure_number_available(
    db: Session, number: int, exclude_id: int | None = None
) -> None:
    """Raise ConflictError if another table already uses `number`."""
    query = select(DiningTable.id).where(DiningTable.number == number)
    if exclude_id is not None:
        query = query.where(DiningTable.id != exclude_id)
    existing_id = db.scalar(query)
    if existing_id is not None:
        logger.warning(
            "Table number %s already taken by table id=%s", number, existing_id
        )
        raise ConflictError(f"Table number {number} already exists", code=CONFLICT_CODE)


def list_tables(
    db: Session, skip: int = 0, limit: int = 100
) -> tuple[list[DiningTable], int]:
    """Return a page of tables ordered by id, plus the total count."""
    total = db.scalar(select(func.count()).select_from(DiningTable)) or 0
    items = db.scalars(
        select(DiningTable).order_by(DiningTable.id).offset(skip).limit(limit)
    ).all()
    return list(items), total


def get_table(db: Session, table_id: int) -> DiningTable:
    """Return the table with `table_id` or raise NotFoundError."""
    table = db.get(DiningTable, table_id)
    if table is None:
        logger.warning("Table id=%s not found", table_id)
        raise NotFoundError(f"Table {table_id} not found", code=NOT_FOUND_CODE)
    return table


def create_table(db: Session, data: DiningTableCreate) -> DiningTable:
    """Create a table. Raise ConflictError if `number` is already in use."""
    _ensure_number_available(db, data.number)
    table = DiningTable(**data.model_dump())
    db.add(table)
    db.flush()
    logger.info("Created table id=%s number=%s", table.id, table.number)
    return table


def update_table(db: Session, table_id: int, data: DiningTableUpdate) -> DiningTable:
    """Replace every field of a table (PUT semantics)."""
    table = get_table(db, table_id)
    _ensure_number_available(db, data.number, exclude_id=table_id)
    for field, value in data.model_dump().items():
        setattr(table, field, value)
    db.flush()
    logger.info("Updated table id=%s", table_id)
    return table


def change_status(db: Session, table_id: int, status: str) -> DiningTable:
    """Change only the status of a table.

    `status` is expected to be validated by the caller (DiningTableStatusUpdate).
    """
    table = get_table(db, table_id)
    previous = table.status
    table.status = status
    db.flush()
    logger.info("Changed status of table id=%s: %s -> %s", table_id, previous, status)
    return table


def delete_table(db: Session, table_id: int) -> None:
    """Delete a table. Raise NotFoundError if it does not exist.

    Raise ConflictError with code "table_in_use" if any order or reservation
    still references the table: deleting would violate their foreign keys and
    Postgres would raise IntegrityError, which the API would surface as a
    generic 500. We check first so the client gets a clear 409.

    Flushes after the delete so later lookups in the same session (e.g.
    get_table) no longer find it. The commit is left to the caller.
    """
    table = get_table(db, table_id)

    has_orders = db.scalar(
        select(Order.id).where(Order.table_id == table_id).limit(1)
    )
    if has_orders is not None:
        logger.warning("Cannot delete table id=%s: has orders", table_id)
        raise ConflictError(
            f"Table {table_id} has orders and cannot be deleted",
            code=TABLE_IN_USE_CODE,
        )

    has_reservations = db.scalar(
        select(Reservation.id).where(Reservation.table_id == table_id).limit(1)
    )
    if has_reservations is not None:
        logger.warning("Cannot delete table id=%s: has reservations", table_id)
        raise ConflictError(
            f"Table {table_id} has reservations and cannot be deleted",
            code=TABLE_IN_USE_CODE,
        )

    db.delete(table)
    db.flush()
    logger.info("Deleted table id=%s", table_id)


def list_available_tables(
    db: Session,
    *,
    reserved_at: datetime,
    party_size: int,
    duration_min: int = DEFAULT_DURATION_MIN,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[DiningTable], int]:
    """Return a page of tables free for `party_size` guests in the given slot (HU-18).

    A table is available when it seats at least `party_size`, it is not
    out of service and no active reservation (status != cancelled) overlaps
    the half-open interval [reserved_at, reserved_at + duration_min), the
    same rule used to reject overlapping reservations (HU-10).
    Tables are ordered by capacity and number, so the best fit comes first.
    """
    if reserved_at.tzinfo is not None:
        reserved_at = reserved_at.astimezone(UTC).replace(tzinfo=None)
    ends_at = reserved_at + timedelta(minutes=duration_min)

    overlapping = exists().where(
        Reservation.table_id == DiningTable.id,
        Reservation.status != CANCELLED,
        Reservation.reserved_at < ends_at,
        reservation_end(Reservation.reserved_at, Reservation.duration_min)
        > reserved_at,
    )
    query = select(DiningTable).where(
        DiningTable.capacity >= party_size,
        DiningTable.status != OUT_OF_SERVICE,
        ~overlapping,
    )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(DiningTable.capacity, DiningTable.number)
        .offset(skip)
        .limit(limit)
    ).all()
    logger.info(
        "Available tables at %s (+%s min) for %s guests: %s",
        reserved_at,
        duration_min,
        party_size,
        total,
    )
    return list(items), total
