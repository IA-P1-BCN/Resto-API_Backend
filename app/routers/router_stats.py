"""Estadísticas para el gerente (HU-15). Solo admin."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import ErrorResponse, UnprocessableError
from app.core.permissions import STATS, require_role
from app.database import get_db
from app.schemas.schema_stats import SalesSummaryOut, TopDishOut
from app.services import stats

router = APIRouter(
    prefix="/stats",
    tags=["stats"],
    dependencies=[Depends(require_role(*STATS))],
)

DbSession = Annotated[Session, Depends(get_db)]

DateFrom = Annotated[
    date | None, Query(
        alias="from", description="First day included (YYYY-MM-DD)")
]
DateTo = Annotated[
    date | None, Query(
        alias="to", description="Last day included (YYYY-MM-DD)")
]
Limit = Annotated[int, Query(
    ge=1, le=50, description="Number of dishes (1-50)")]

ERRORS = {
    422: {"model": ErrorResponse, "description": "`from` is after `to`"},
}


def _check_dates(date_from: date | None, date_to: date | None) -> None:
    if date_from and date_to and date_from > date_to:
        raise UnprocessableError(
            "from must be before to", code="invalid_date_range")


@router.get(
    "/sales",
    response_model=SalesSummaryOut,
    responses=ERRORS,
    summary="Sales summary",
    description="Orders count, total sales and average ticket, with a daily "
    "breakdown. Counts orders in status `served` or `paid`. Optional filters "
    "`from` and `to` (creation date, both included). Role: admin.",
)
def get_sales(db: DbSession, date_from: DateFrom = None, date_to: DateTo = None):
    _check_dates(date_from, date_to)
    return stats.sales_summary(db, date_from, date_to)


@router.get(
    "/top-dishes",
    response_model=list[TopDishOut],
    responses=ERRORS,
    summary="Best-selling dishes",
    description="Dishes ordered by units sold, with their revenue. Counts orders "
    "in status `served` or `paid`. Optional filters `from` and `to` (creation "
    "date, both included) and `limit` (default 5, max 50). Role: admin.",
)
def get_top_dishes(
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    limit: Limit = 5,
):
    _check_dates(date_from, date_to)
    return stats.top_dishes(db, date_from, date_to, limit)
