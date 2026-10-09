"""Exportación de facturas y pedidos a CSV (HU-14)."""

import csv
import io
from decimal import Decimal

import pytest

from app.models.dining_table import DiningTable
from app.models.model_category import Category
from app.models.model_dish import Dish
from app.models.model_order import Order
from app.models.model_order_item import OrderItem
from app.models.model_user import Role
from app.services.csv_export import INVOICE_COLUMNS, ORDER_COLUMNS, export_filename


@pytest.fixture
def admin(auth_headers):
    return auth_headers(Role.admin)


@pytest.fixture
def orders(db):
    """Dos pedidos con 2 platos cada uno: uno servido y otro pendiente."""
    category = Category(name="Principales")
    db.add(category)
    db.flush()
    dish = Dish(name="Pasta", price=Decimal("11.00"), category_id=category.id)
    db.add(dish)
    db.flush()
    ids = []
    for number, status in [(1, "served"), (2, "pending")]:
        table = DiningTable(number=number, capacity=4, location="terrace")
        db.add(table)
        db.flush()
        order = Order(table_id=table.id, total=Decimal("22.00"), status=status)
        db.add(order)
        db.flush()
        db.add(
            OrderItem(
                order_id=order.id,
                dish_id=dish.id,
                quantity=2,
                unit_price=Decimal("11.00"),
            )
        )
        ids.append(order.id)
    db.commit()
    return ids


def _rows(response) -> list[dict[str, str]]:
    """Lee el CSV de la respuesta como lista de diccionarios."""
    text = response.content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def test_export_invoices_is_a_csv_download(client, admin, orders):
    client.post(f"/orders/{orders[0]}/invoice", headers=admin)

    r = client.get("/exports/invoices", headers=admin)

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.headers["content-disposition"] == 'attachment; filename="invoices.csv"'
    # BOM al principio para que Excel lea bien los acentos.
    assert r.content.startswith(b"\xef\xbb\xbf")


def test_export_invoices_content(client, admin, orders):
    client.post(f"/orders/{orders[0]}/invoice", headers=admin)

    r = client.get("/exports/invoices", headers=admin)

    header = r.content.decode("utf-8-sig").splitlines()[0]
    assert header == ",".join(INVOICE_COLUMNS)
    [row] = _rows(r)
    assert row["number"].endswith("-00001")
    assert row["order_id"] == str(orders[0])
    assert row["base_amount"] == "20.00"
    assert row["tax_amount"] == "2.00"
    assert row["total"] == "22.00"


def test_export_invoices_without_invoices_has_only_the_header(client, admin):
    r = client.get("/exports/invoices", headers=admin)

    assert r.status_code == 200
    assert _rows(r) == []


def test_export_orders_content(client, admin, orders):
    client.post(f"/orders/{orders[0]}/invoice", headers=admin)

    r = client.get("/exports/orders", headers=admin)

    assert r.headers["content-disposition"] == 'attachment; filename="orders.csv"'
    header = r.content.decode("utf-8-sig").splitlines()[0]
    assert header == ",".join(ORDER_COLUMNS)
    served, pending = _rows(r)
    assert served["status"] == "served"
    assert served["items"] == "2"
    assert served["total"] == "22.00"
    assert served["invoice_number"].endswith("-00001")
    assert pending["invoice_number"] == ""


def test_export_orders_filters_by_status(client, admin, orders):
    r = client.get("/exports/orders",
                   params={"status": "pending"}, headers=admin)

    assert [row["id"] for row in _rows(r)] == [str(orders[1])]


def test_export_orders_rejects_unknown_status(client, admin):
    r = client.get("/exports/orders", params={"status": "nope"}, headers=admin)

    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"


def test_export_filename_includes_the_dates(client, admin):
    r = client.get(
        "/exports/orders",
        params={"date_from": "2026-01-01", "date_to": "2026-01-31"},
        headers=admin,
    )
    assert (
        r.headers["content-disposition"]
        == 'attachment; filename="orders_2026-01-01_2026-01-31.csv"'
    )


def test_export_rejects_inverted_dates(client, admin):
    r = client.get(
        "/exports/invoices",
        params={"date_from": "2026-03-01", "date_to": "2026-02-01"},
        headers=admin,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "invalid_date_range"


@pytest.mark.parametrize("path", ["/exports/invoices", "/exports/orders"])
def test_only_admin_can_export(client, auth_headers, path):
    assert client.get(path, headers=auth_headers(
        Role.waiter)).status_code == 403
    assert client.get(path).status_code == 401


def test_export_filename_helper():
    from datetime import date

    assert export_filename("invoices") == "invoices.csv"
    assert (
        export_filename("invoices", date(2026, 1, 1)
                        ) == "invoices_from_2026-01-01.csv"
    )
    assert (
        export_filename("orders", None, date(2026, 1, 31))
        == "orders_until_2026-01-31.csv"
    )
