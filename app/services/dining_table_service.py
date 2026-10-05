"""
Business logic for dining tables (HU-09).

Assumptions: see PENDING-CONTRACTS.md (E1 for exceptions, P1 for
pagination).
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

# ASSUMPTION E1: app.core.exceptions define NotFoundError y ConflictError,
# ambas heredando de HTTPException. Ver PENDING-CONTRACTS.md.
from app.core.exceptions import ConflictError, NotFoundError
from app.models.dining_table import DiningTable
from app.schemas.dining_table import DiningTableCreate, DiningTableUpdate

logger = logging.getLogger(__name__)

# ASSUMPTION: code por confirmar con Rita.
CONFLICT_CODE = "conflict"
# ASSUMPTION: code por confirmar con Rita.
NOT_FOUND_CODE = "not_found"

# El servicio nunca hace commit: la transacción la gestiona el caller
# (router o fixture de test). Hace add/flush/delete y deja la sesión
# consistente para consultas posteriores.


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

    Flushes after the delete so later lookups in the same session (e.g.
    get_table) no longer find it. The commit is left to the caller.
    """
    table = get_table(db, table_id)
    db.delete(table)
    db.flush()
    logger.info("Deleted table id=%s", table_id)
