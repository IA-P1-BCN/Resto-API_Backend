"""Estadísticas para el gerente (HU-15). Solo admin."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import ErrorResponse, UnprocessableError
from app.core.permissions import STATS, require_role
from app.database import get_db
from app.schemas.schema_stats import SalesSummaryOut
from app.services import stats

router = APIRouter(
    prefix="/stats",
    tags=["stats"],
    dependencies=[Depends(require_role(*STATS))],
)

DbSession = Annotated[Session, Depends(get_db)]

# En la URL se llaman `from` y `to`; en Python `from` es palabra reservada,
# así que el parámetro se llama date_from y `alias` le da el nombre público.
DateFrom = Annotated[
    date | None, Query(
        alias="from", description="First day included (YYYY-MM-DD)")
]
DateTo = Annotated[
    date | None, Query(
        alias="to", description="Last day included (YYYY-MM-DD)")
]

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
