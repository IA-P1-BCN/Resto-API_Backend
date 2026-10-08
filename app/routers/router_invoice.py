from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import ErrorResponse, UnprocessableError
from app.core.pagination import Page, PageParamsDep
from app.core.permissions import INVOICES, require_role
from app.database import get_db
from app.schemas.schema_invoice import InvoiceOut
from app.services import invoices as invoice_service

router = APIRouter(tags=["invoices"])

DbSession = Annotated[Session, Depends(get_db)]

STAFF = [Depends(require_role(*INVOICES))]


@router.post(
    "/orders/{order_id}/invoice",
    response_model=InvoiceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=STAFF,
    summary="Generate the invoice of an order",
    description="Only for orders in status `served`, once per order. "
    "Prices include 10% VAT. Roles: admin, waiter.",
    responses={
        404: {"model": ErrorResponse, "description": "Order not found"},
        409: {
            "model": ErrorResponse,
            "description": "Order not served (`order_not_served`) or already "
            "invoiced (`invoice_already_exists`)",
        },
    },
)
def create_invoice(order_id: int, db: DbSession):
    return invoice_service.create_invoice(db, order_id)


@router.get(
    "/invoices",
    response_model=Page[InvoiceOut],
    dependencies=STAFF,
    summary="List invoices",
    description="Paginated list ordered by invoice number. Optional filters by "
    "issue date (`date_from`, `date_to`, both included). Roles: admin, waiter.",
)
def list_invoices(
    db: DbSession,
    params: PageParamsDep,
    date_from: date | None = None,
    date_to: date | None = None,
):
    if date_from and date_to and date_from > date_to:
        raise UnprocessableError(
            "date_from must be before date_to", code="invalid_date_range"
        )
    return invoice_service.list_invoices(db, params, date_from, date_to)


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceOut,
    dependencies=STAFF,
    summary="Get an invoice",
    description="Roles: admin, waiter.",
    responses={404: {"model": ErrorResponse,
                     "description": "Invoice not found"}},
)
def get_invoice(invoice_id: int, db: DbSession):
    return invoice_service.get_invoice_or_404(db, invoice_id)
