"""Cálculo del IVA y numeración de facturas (HU-14)."""

from decimal import Decimal

import pytest

from app.models.dining_table import DiningTable
from app.models.model_invoice import Invoice
from app.models.model_order import Order
from app.services.invoices import format_invoice_number, next_sequence, split_tax


@pytest.mark.parametrize(
    ("total", "base", "tax"),
    [
        ("22.00", "20.00", "2.00"),
        ("10.50", "9.55", "0.95"),
        ("9.99", "9.08", "0.91"),
        ("0.01", "0.01", "0.00"),
        ("0", "0.00", "0.00"),
    ],
)
def test_split_tax_with_vat_included(total, base, tax):
    assert split_tax(Decimal(total)) == (Decimal(base), Decimal(tax))


def test_split_tax_always_adds_up_to_the_total():
    for cents in range(0, 10_000, 7):
        total = Decimal(cents) / 100
        base, tax = split_tax(total)
        assert base + tax == total


def test_format_invoice_number_pads_with_zeros():
    assert format_invoice_number(2026, 1) == "F-2026-00001"
    assert format_invoice_number(2027, 153) == "F-2027-00153"


def _add_invoice(db, year: int, sequence: int) -> None:
    table = DiningTable(number=year * 1000 + sequence,
                        capacity=2, location="terrace")
    db.add(table)
    db.flush()
    order = Order(table_id=table.id, total=Decimal("11.00"), status="served")
    db.add(order)
    db.flush()
    db.add(
        Invoice(
            number=format_invoice_number(year, sequence),
            year=year,
            sequence=sequence,
            order_id=order.id,
            base_amount=Decimal("10.00"),
            tax_rate=Decimal("0.10"),
            tax_amount=Decimal("1.00"),
            total=Decimal("11.00"),
        )
    )
    db.commit()


def test_first_invoice_of_the_year_is_number_one(db):
    assert next_sequence(db, 2026) == 1


def test_sequence_continues_within_the_year(db):
    _add_invoice(db, 2026, 1)
    _add_invoice(db, 2026, 2)
    assert next_sequence(db, 2026) == 3


def test_sequence_restarts_every_year(db):
    _add_invoice(db, 2025, 1)
    _add_invoice(db, 2025, 2)
    assert next_sequence(db, 2026) == 1
