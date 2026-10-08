"""
HTTP routes for dining tables (HU-09).

Assumptions: see PENDING-CONTRACTS.md (A5 for auth, D3/D4 for the
session and transactions, P1 for pagination, E1 for exceptions).
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# ASSUMPTION D3: app.core.database expone get_db (generador sync de Session
# que NO hace commit; solo yield + close). Ver PENDING-CONTRACTS.md.
from app.core.database import get_db
from app.core.permissions import TABLES, require_role
from app.models.dining_table import DiningTable
from app.models.model_user import Role
from app.models.reservation import DEFAULT_DURATION_MIN
from app.schemas.dining_table import (
    DiningTableCreate,
    DiningTableRead,
    DiningTableStatusUpdate,
    DiningTableUpdate,
)
from app.schemas.reservation import MAX_DURATION_MIN
from app.services import dining_table_service

router = APIRouter(prefix="/tables", tags=["tables"])

DbSession = Annotated[Session, Depends(get_db)]

# require_role ya depende de get_current_user: sin token → 401, rol no permitido → 403.
ADMIN_ONLY = [Depends(require_role(Role.admin))]
ADMIN_OR_WAITER = [Depends(require_role(*TABLES))]


# ASSUMPTION P1: paginación inline mientras no conozcamos el helper de
# app.core.pagination (Rita). Se migrará a ese helper cuando llegue.
class DiningTablePage(BaseModel):
    """Paginated list of dining tables."""

    items: list[DiningTableRead] = Field(description="Tables in this page.")
    total: int = Field(description="Total number of tables.", examples=[42])
    page: int = Field(description="Current page (1-based).", examples=[1])
    size: int = Field(description="Page size.", examples=[20])


@router.get(
    "",
    response_model=DiningTablePage,
    status_code=status.HTTP_200_OK,
    dependencies=ADMIN_OR_WAITER,
    summary="List dining tables",
    description="Paginated list of tables ordered by id. Roles: admin, waiter.",
)
def list_tables(
    db: DbSession,
    page: Annotated[int, Query(ge=1, description="Page number (1-based).")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Items per page.")] = 20,
) -> DiningTablePage:
    items, total = dining_table_service.list_tables(
        db, skip=(page - 1) * size, limit=size
    )
    return DiningTablePage(
        items=[DiningTableRead.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


# Debe declararse antes de /{table_id}: si no, "available" se tomaría como id.
@router.get(
    "/available",
    response_model=DiningTablePage,
    status_code=status.HTTP_200_OK,
    dependencies=ADMIN_OR_WAITER,
    summary="List available dining tables",
    description="Tables that seat at least `party_size` guests, are not "
    "`out_of_service` and have no active reservation overlapping "
    "[`reserved_at`, `reserved_at` + `duration_min`). Ordered by capacity, so "
    "the best fit comes first. Roles: admin, waiter.",
)
def list_available_tables(
    db: DbSession,
    reserved_at: Annotated[
        datetime,
        Query(
            description="Start of the slot. Without time zone; if one is sent "
            "it is converted to UTC.",
            examples=["2026-10-10T21:00:00"],
        ),
    ],
    party_size: Annotated[
        int, Query(gt=0, description="Number of guests.", examples=[4])
    ],
    duration_min: Annotated[
        int,
        Query(
            gt=0,
            le=MAX_DURATION_MIN,
            description="Length of the slot in minutes.",
            examples=[DEFAULT_DURATION_MIN],
        ),
    ] = DEFAULT_DURATION_MIN,
    page: Annotated[int, Query(ge=1, description="Page number (1-based).")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Items per page.")] = 20,
) -> DiningTablePage:
    items, total = dining_table_service.list_available_tables(
        db,
        reserved_at=reserved_at,
        party_size=party_size,
        duration_min=duration_min,
        skip=(page - 1) * size,
        limit=size,
    )
    return DiningTablePage(
        items=[DiningTableRead.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/{table_id}",
    response_model=DiningTableRead,
    status_code=status.HTTP_200_OK,
    dependencies=ADMIN_OR_WAITER,
    summary="Get a dining table",
    description="Return one table by id. 404 if it does not exist. "
    "Roles: admin, waiter.",
)
def get_table(table_id: int, db: DbSession) -> DiningTable:
    return dining_table_service.get_table(db, table_id)


# ASSUMPTION D4: como get_db no hace commit, el router confirma (o deshace)
# la transacción en cada endpoint que escribe.
@router.post(
    "",
    response_model=DiningTableRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=ADMIN_ONLY,
    summary="Create a dining table",
    description="Create a new table. 409 if `number` is already in use. Roles: admin.",
)
def create_table(data: DiningTableCreate, db: DbSession) -> DiningTable:
    try:
        table = dining_table_service.create_table(db, data)
        db.commit()
        db.refresh(table)
        return table
    except Exception:
        db.rollback()
        raise


@router.put(
    "/{table_id}",
    response_model=DiningTableRead,
    status_code=status.HTTP_200_OK,
    dependencies=ADMIN_ONLY,
    summary="Replace a dining table",
    description="Full replacement: every field is required. 404 if the table "
    "does not exist, 409 if `number` belongs to another table. Roles: admin.",
)
def update_table(table_id: int, data: DiningTableUpdate, db: DbSession) -> DiningTable:
    try:
        table = dining_table_service.update_table(db, table_id, data)
        db.commit()
        db.refresh(table)
        return table
    except Exception:
        db.rollback()
        raise


@router.patch(
    "/{table_id}/status",
    response_model=DiningTableRead,
    status_code=status.HTTP_200_OK,
    dependencies=ADMIN_OR_WAITER,
    summary="Change the status of a dining table",
    description="Update only `status`. 404 if the table does not exist. "
    "Roles: admin, waiter.",
)
def change_table_status(
    table_id: int, data: DiningTableStatusUpdate, db: DbSession
) -> DiningTable:
    try:
        table = dining_table_service.change_status(db, table_id, data.status)
        db.commit()
        db.refresh(table)
        return table
    except Exception:
        db.rollback()
        raise


@router.delete(
    "/{table_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=ADMIN_ONLY,
    summary="Delete a dining table",
    description="Delete a table. 404 if it does not exist. Roles: admin.",
)
def delete_table(table_id: int, db: DbSession) -> None:
    dining_table_service.delete_table(db, table_id)
    db.commit()
