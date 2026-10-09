"""Facturas: generar, listar y consultar (HU-14)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.dining_table import DiningTable
from app.models.model_invoice import Invoice
from app.models.model_order import Order
from app.models.model_user import Role


@pytest.fixture
def make_order(db):
    """Crea un pedido con el total y el estado indicados, en una mesa nueva."""
    counter = {"table": 0}

    def _make(total: str = "22.00", status: str = "served") -> int:
        counter["table"] += 1
        table = DiningTable(
            number=counter["table"], capacity=4, location="terrace")
        db.add(table)
        db.flush()
        order = Order(table_id=table.id, total=Decimal(total), status=status)
        db.add(order)
        db.commit()
        return order.id

    return _make


@pytest.fixture
def admin(auth_headers):
    return auth_headers(Role.admin)


def test_create_invoice_for_served_order(client, admin, make_order):
    order_id = make_order("22.00")

    r = client.post(f"/orders/{order_id}/invoice", headers=admin)

    assert r.status_code == 201
    data = r.json()
    assert data["number"] == f"F-{datetime.now(UTC).year}-00001"
    assert data["order_id"] == order_id
    assert data["base_amount"] == "20.00"
    assert data["tax_rate"] == "0.10"
    assert data["tax_amount"] == "2.00"
    assert data["total"] == "22.00"


def test_base_plus_tax_is_always_the_order_total(client, admin, make_order):
    order_id = make_order("10.50")

    data = client.post(f"/orders/{order_id}/invoice", headers=admin).json()

    assert data["base_amount"] == "9.55"
    assert data["tax_amount"] == "0.95"
    assert Decimal(data["base_amount"]) + Decimal(data["tax_amount"]) == Decimal(
        "10.50"
    )


def test_invoice_numbers_are_consecutive(client, admin, make_order):
    first = client.post(
        f"/orders/{make_order()}/invoice", headers=admin).json()
    second = client.post(
        f"/orders/{make_order()}/invoice", headers=admin).json()

    assert first["number"].endswith("-00001")
    assert second["number"].endswith("-00002")


def test_order_stays_served_after_invoicing(client, db, admin, make_order):
    order_id = make_order()

    client.post(f"/orders/{order_id}/invoice", headers=admin)

    db.expire_all()
    assert db.get(Order, order_id).status == "served"


@pytest.mark.parametrize("status", ["pending", "in_kitchen", "paid", "cancelled"])
def test_only_served_orders_can_be_invoiced(client, admin, make_order, status):
    order_id = make_order(status=status)

    r = client.post(f"/orders/{order_id}/invoice", headers=admin)

    assert r.status_code == 409
    assert r.json()["code"] == "order_not_served"


def test_order_cannot_be_invoiced_twice(client, admin, make_order):
    order_id = make_order()
    client.post(f"/orders/{order_id}/invoice", headers=admin)

    r = client.post(f"/orders/{order_id}/invoice", headers=admin)

    assert r.status_code == 409
    assert r.json()["code"] == "invoice_already_exists"


def test_invoice_for_unknown_order_returns_404(client, admin):
    r = client.post("/orders/999/invoice", headers=admin)

    assert r.status_code == 404
    assert r.json() == {"detail": "Order not found", "code": "not_found"}


def test_waiter_can_create_invoice(client, auth_headers, make_order):
    r = client.post(
        f"/orders/{make_order()}/invoice", headers=auth_headers(Role.waiter)
    )
    assert r.status_code == 201


@pytest.mark.parametrize("role", [Role.kitchen, Role.customer])
def test_other_roles_cannot_create_invoice(client, auth_headers, make_order, role):
    r = client.post(f"/orders/{make_order()}/invoice",
                    headers=auth_headers(role))
    assert r.status_code == 403


def test_create_invoice_without_token_returns_401(client, make_order):
    r = client.post(f"/orders/{make_order()}/invoice")
    assert r.status_code == 401


def test_list_invoices_is_paginated_and_ordered(client, admin, make_order):
    for _ in range(3):
        client.post(f"/orders/{make_order()}/invoice", headers=admin)

    r = client.get("/invoices", params={"page": 1, "size": 2}, headers=admin)

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["size"] == 2
    assert [i["number"][-5:] for i in data["items"]] == ["00001", "00002"]


def test_list_invoices_filters_by_issue_date(client, db, admin, make_order):
    for _ in range(2):
        client.post(f"/orders/{make_order()}/invoice", headers=admin)
    first = db.get(Invoice, 1)
    first.issued_at = datetime(
        2026, 1, 15, 23, 59, tzinfo=UTC).replace(tzinfo=None)
    db.commit()

    r = client.get(
        "/invoices",
        params={"date_from": "2026-01-15", "date_to": "2026-01-15"},
        headers=admin,
    )

    assert [i["id"] for i in r.json()["items"]] == [1]


def test_list_invoices_rejects_inverted_dates(client, admin):
    r = client.get(
        "/invoices",
        params={"date_from": "2026-03-01", "date_to": "2026-02-01"},
        headers=admin,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "invalid_date_range"


def test_get_invoice(client, admin, make_order):
    created = client.post(
        f"/orders/{make_order()}/invoice", headers=admin).json()

    r = client.get(f"/invoices/{created['id']}", headers=admin)

    assert r.status_code == 200
    assert r.json() == created


def test_get_unknown_invoice_returns_404(client, admin):
    r = client.get("/invoices/999", headers=admin)
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"


def test_customer_cannot_list_invoices(client, auth_headers):
    r = client.get("/invoices", headers=auth_headers(Role.customer))
    assert r.status_code == 403
