from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.exceptions import UnprocessableError
from app.core.permissions import require_role
from app.database import get_db
from app.models.model_user import Role
from app.services import csv_export

router = APIRouter(prefix="/exports", tags=["exports"])

DbSession = Annotated[Session, Depends(get_db)]

ADMIN_ONLY = [Depends(require_role(Role.admin))]

OrderStatus = Literal["pending", "in_kitchen", "served", "paid", "cancelled"]

CSV_RESPONSE = {
    200: {
        "content": {"text/csv": {}},
        "description": "CSV file (download)",
    }
}


def _check_dates(date_from: date | None, date_to: date | None) -> None:
    if date_from and date_to and date_from > date_to:
        raise UnprocessableError(
            "date_from must be before date_to", code="invalid_date_range"
        )


def _csv_response(content: str, filename: str) -> Response:
    """Respuesta que el navegador descarga como archivo en vez de mostrarla."""
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/invoices",
    dependencies=ADMIN_ONLY,
    response_class=Response,
    responses=CSV_RESPONSE,
    summary="Export invoices to CSV",
    description="Invoices ordered by number. Optional filters by issue date "
    "(`date_from`, `date_to`, both included). Role: admin.",
)
def export_invoices(
    db: DbSession, date_from: date | None = None, date_to: date | None = None
):
    _check_dates(date_from, date_to)
    content = csv_export.invoices_csv(db, date_from, date_to)
    filename = csv_export.export_filename("invoices", date_from, date_to)
    return _csv_response(content, filename)


@router.get(
    "/orders",
    dependencies=ADMIN_ONLY,
    response_class=Response,
    responses=CSV_RESPONSE,
    summary="Export orders to CSV",
    description="Orders ordered by id, with the number of items and the invoice "
    "number if they have one. Optional filters by `status` and creation date "
    "(`date_from`, `date_to`, both included). Role: admin.",
)
def export_orders(
    db: DbSession,
    status: OrderStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    _check_dates(date_from, date_to)
    content = csv_export.orders_csv(db, status, date_from, date_to)
    filename = csv_export.export_filename("orders", date_from, date_to)
    return _csv_response(content, filename)
