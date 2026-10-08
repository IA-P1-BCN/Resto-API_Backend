"""Facturas de pedidos (HU-14).

Decisiones (issue #12):
- Solo se factura un pedido en estado `served`, y una sola vez.
- Los precios llevan el IVA incluido: base = total / (1 + IVA) e IVA = total - base.
- Número `F-AÑO-NNNNN`, con un correlativo que vuelve a 1 cada año.
- Facturar no cambia el estado del pedido (sigue `served`; luego se marca `paid`).
"""

import logging
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.model_invoice import Invoice
from app.models.model_order import Order

logger = logging.getLogger(__name__)

TAX_RATE = Decimal("0.10")
INVOICEABLE_STATUS = "served"
CENT = Decimal("0.01")


def split_tax(total: Decimal, tax_rate: Decimal = TAX_RATE) -> tuple[Decimal, Decimal]:
    """Separa un total con IVA incluido en (base, cuota de IVA), redondeado a céntimos.

    La cuota se calcula como total - base para que base + IVA sea siempre el total.
    """
    total = Decimal(total).quantize(CENT, rounding=ROUND_HALF_UP)
    base = (total / (1 + tax_rate)).quantize(CENT, rounding=ROUND_HALF_UP)
    return base, total - base


def format_invoice_number(year: int, sequence: int) -> str:
    """F-2026-00001"""
    return f"F-{year}-{sequence:05d}"


def next_sequence(db: Session, year: int) -> int:
    """Siguiente número correlativo del año (1 si es la primera factura del año)."""
    last = db.scalar(select(func.max(Invoice.sequence)
                            ).where(Invoice.year == year))
    return (last or 0) + 1


def create_invoice(db: Session, order_id: int) -> Invoice:
    """Genera la factura de un pedido servido. 404 si no existe, 409 si no se puede."""
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("Order not found")
    if order.status != INVOICEABLE_STATUS:
        raise ConflictError(
            f"Only served orders can be invoiced (current status: {order.status})",
            code="order_not_served",
        )
    if order.invoice is not None:
        raise ConflictError(
            f"Order {order_id} already has invoice {order.invoice.number}",
            code="invoice_already_exists",
        )

    issued_at = datetime.now(UTC).replace(tzinfo=None)
    year = issued_at.year
    sequence = next_sequence(db, year)
    base, tax = split_tax(order.total)

    invoice = Invoice(
        number=format_invoice_number(year, sequence),
        year=year,
        sequence=sequence,
        order_id=order.id,
        base_amount=base,
        tax_rate=TAX_RATE,
        tax_amount=tax,
        total=base + tax,
        issued_at=issued_at,
    )
    db.add(invoice)
    try:
        db.commit()
    except IntegrityError as exc:
        # Dos peticiones a la vez: otra factura se ha llevado el mismo número
        # o el mismo pedido. La BD lo impide y respondemos 409.
        db.rollback()
        raise ConflictError(
            "The invoice could not be created, please try again",
            code="invoice_conflict",
        ) from exc
    db.refresh(invoice)

    logger.info(
        "Invoice issued",
        extra={"invoice_number": invoice.number, "order_id": order.id},
    )
    return invoice
