from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import ErrorResponse
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
