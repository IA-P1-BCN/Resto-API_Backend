"""Tests unitarios de create_invoice cuando la BD rechaza la factura (HU-14).

Simula dos peticiones a la vez que calculan el mismo número correlativo: la
restricción única (year, sequence) salta y el servicio responde 409.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.exceptions import ConflictError
from app.models.dining_table import DiningTable
from app.models.model_invoice import Invoice
from app.models.model_order import Order
from app.services import invoices as service


@pytest.fixture
def served_orders(db) -> list[Order]:
    table = DiningTable(number=1, capacity=4, location="indoor")
    db.add(table)
    db.flush()
    orders = [Order(table_id=table.id, total=Decimal("22.00"), status="served") for _ in range(2)]
    db.add_all(orders)
    db.commit()
    return orders


def test_duplicated_sequence_raises_conflict_and_rolls_back(db, served_orders, monkeypatch):
    first, second = served_orders
    service.create_invoice(db, first.id)
    monkeypatch.setattr(service, "next_sequence", lambda db, year: 1)

    with pytest.raises(ConflictError) as exc:
        service.create_invoice(db, second.id)

    assert exc.value.status_code == 409
    assert exc.value.code == "invoice_conflict"
    assert db.query(Invoice).count() == 1
    assert db.get(Order, second.id).invoice is None


def test_invoice_uses_ten_percent_vat(db, served_orders):
    invoice = service.create_invoice(db, served_orders[0].id)

    assert invoice.tax_rate == Decimal("0.10")
    assert invoice.base_amount == Decimal("20.00")
    assert invoice.tax_amount == Decimal("2.00")
    assert invoice.number == f"F-{datetime.now(UTC).year}-00001"
