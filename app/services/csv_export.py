"""Exportación a CSV de facturas y pedidos para contabilidad (HU-14).

Formato: separador `,`, decimales con punto, fechas ISO y UTF-8 con BOM para que
Excel muestre bien los acentos al abrir el archivo.
"""

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.model_invoice import Invoice
from app.models.model_order import Order
from app.services.invoices import invoices_query

INVOICE_COLUMNS = [
    "number",
    "issued_at",
    "order_id",
    "table_id",
    "base_amount",
    "tax_rate",
    "tax_amount",
    "total",
]

ORDER_COLUMNS = [
    "id",
    "created_at",
    "table_id",
    "waiter_id",
    "status",
    "items",
    "total",
    "invoice_number",
]


def _cell(value: object) -> object:
    """Fechas en ISO 8601 y vacío en vez de None; el resto, tal cual."""
    if value is None:
        return ""
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def to_csv(columns: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    """Construye el texto CSV con una fila de cabecera."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_cell(value) for value in row])
    return buffer.getvalue()


def export_filename(
    prefix: str, date_from: date | None = None, date_to: date | None = None
) -> str:
    """invoices.csv, invoices_from_2026-01-01.csv, invoices_2026-01-01_2026-01-31.csv"""
    if date_from and date_to:
        return f"{prefix}_{date_from}_{date_to}.csv"
    if date_from:
        return f"{prefix}_from_{date_from}.csv"
    if date_to:
        return f"{prefix}_until_{date_to}.csv"
    return f"{prefix}.csv"


def invoices_csv(
    db: Session, date_from: date | None = None, date_to: date | None = None
) -> str:
    stmt = invoices_query(date_from, date_to).options(
        selectinload(Invoice.order))
    invoices = db.scalars(stmt).all()
    rows = (
        [
            invoice.number,
            invoice.issued_at,
            invoice.order_id,
            invoice.order.table_id,
            invoice.base_amount,
            invoice.tax_rate,
            invoice.tax_amount,
            invoice.total,
        ]
        for invoice in invoices
    )
    return to_csv(INVOICE_COLUMNS, rows)


def orders_csv(
    db: Session,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> str:
    stmt = select(Order).options(selectinload(
        Order.items), selectinload(Order.invoice))
    if status is not None:
        stmt = stmt.where(Order.status == status)
    if date_from is not None:
        stmt = stmt.where(Order.created_at >=
                          datetime.combine(date_from, time.min))
    if date_to is not None:
        next_day = datetime.combine(date_to + timedelta(days=1), time.min)
        stmt = stmt.where(Order.created_at < next_day)
    orders = db.scalars(stmt.order_by(Order.id)).all()
    rows = (
        [
            order.id,
            order.created_at,
            order.table_id,
            order.waiter_id,
            order.status,
            sum(item.quantity for item in order.items),
            order.total,
            order.invoice.number if order.invoice else None,
        ]
        for order in orders
    )
    return to_csv(ORDER_COLUMNS, rows)
