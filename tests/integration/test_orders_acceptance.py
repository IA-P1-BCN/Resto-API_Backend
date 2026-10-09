"""Tests de integración de /orders (HU-07): total, platos no disponibles y estados.

Complementan tests/test_order.py: total con varias líneas, formato de error
{"detail", "code"}, filtros de listado y transiciones de estado no válidas.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from app.models.dining_table import DiningTable
from app.models.model_category import Category
from app.models.model_dish import Dish
from app.models.model_order import Order
from app.models.model_user import Role

MISSING_ID = 999_999


def _assert_error(response: Any, status_code: int, code: str) -> None:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["code"] == code


@pytest.fixture
def menu(db) -> dict[str, int]:
    """Dos mesas, dos platos disponibles y uno sin stock."""
    category = Category(name="Principales")
    db.add(category)
    db.flush()
    tables = [DiningTable(number=n, capacity=4, location="indoor") for n in (1, 2)]
    dishes = {
        "pasta": Dish(name="Pasta", price=Decimal("10.50"), is_available=True, category_id=category.id),
        "vino": Dish(name="Vino", price=Decimal("3.25"), is_available=True, category_id=category.id),
        "agotado": Dish(name="Agotado", price=Decimal("8.00"), is_available=False, category_id=category.id),
    }
    db.add_all([*tables, *dishes.values()])
    db.commit()
    return {
        "table": tables[0].id,
        "other_table": tables[1].id,
        **{name: dish.id for name, dish in dishes.items()},
    }


@pytest.fixture
def waiter(auth_headers) -> dict[str, str]:
    return auth_headers(Role.waiter)


def _order(client, headers, table_id: int, items: list[tuple[int, int]]):
    return client.post("/orders/", headers=headers, json={
        "table_id": table_id,
        "items": [{"dish_id": dish_id, "quantity": qty} for dish_id, qty in items],
    })


def test_order_total_is_sum_of_quantity_by_unit_price(client, menu, waiter):
    r = _order(client, waiter, menu["table"], [(menu["pasta"], 2), (menu["vino"], 3)])

    assert r.status_code == 201
    body = r.json()
    lines = sum(Decimal(i["quantity"]) * Decimal(i["unit_price"]) for i in body["items"])
    assert Decimal(body["total"]) == lines == Decimal("30.75")
    assert body["status"] == "pending"


def test_order_keeps_unit_price_when_dish_price_changes(client, db, menu, waiter):
    order_id = _order(client, waiter, menu["table"], [(menu["pasta"], 1)]).json()["id"]
    db.get(Dish, menu["pasta"]).price = Decimal("99.00")
    db.commit()

    r = client.get(f"/orders/{order_id}", headers=waiter)

    assert Decimal(r.json()["items"][0]["unit_price"]) == Decimal("10.50")
    assert Decimal(r.json()["total"]) == Decimal("10.50")


def test_order_with_unavailable_dish_returns_409_and_saves_nothing(client, db, menu, waiter):
    r = _order(client, waiter, menu["table"], [(menu["pasta"], 1), (menu["agotado"], 1)])

    _assert_error(r, 409, "conflict")
    assert db.query(Order).count() == 0


def test_order_with_unknown_dish_returns_409(client, menu, waiter):
    _assert_error(_order(client, waiter, menu["table"], [(MISSING_ID, 1)]), 409, "conflict")


def test_order_on_unknown_table_returns_404(client, menu, waiter):
    _assert_error(_order(client, waiter, MISSING_ID, [(menu["pasta"], 1)]), 404, "not_found")


def test_order_without_items_field_returns_422(client, menu, waiter):
    r = client.post("/orders/", headers=waiter, json={"table_id": menu["table"]})

    _assert_error(r, 422, "validation_error")


def test_list_orders_filters_by_table(client, menu, waiter):
    _order(client, waiter, menu["table"], [(menu["pasta"], 1)])
    _order(client, waiter, menu["other_table"], [(menu["vino"], 1)])

    r = client.get("/orders/", headers=waiter, params={"table_id": menu["other_table"]})

    assert r.status_code == 200
    assert [o["table_id"] for o in r.json()] == [menu["other_table"]]


def test_list_orders_filters_by_dates(client, menu, waiter):
    _order(client, waiter, menu["table"], [(menu["pasta"], 1)])
    today = datetime.now(UTC).date()
    yesterday, later = today - timedelta(days=1), today + timedelta(days=2)

    inside = client.get("/orders/", headers=waiter,
                        params={"date_from": str(yesterday), "date_to": str(later)})
    future = client.get("/orders/", headers=waiter, params={"date_from": str(later)})
    past = client.get("/orders/", headers=waiter, params={"date_to": str(yesterday)})

    assert len(inside.json()) == 1
    assert future.json() == []
    assert past.json() == []


def test_list_orders_invalid_date_returns_422(client, waiter):
    r = client.get("/orders/", headers=waiter, params={"date_from": "ayer"})

    _assert_error(r, 422, "validation_error")


def test_get_unknown_order_returns_404(client, waiter):
    _assert_error(client.get(f"/orders/{MISSING_ID}", headers=waiter), 404, "not_found")


def _set_status(client, headers, order_id: int, status: str):
    return client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": status})


def test_full_order_lifecycle_until_paid(client, menu, waiter, auth_headers):
    order_id = _order(client, waiter, menu["table"], [(menu["pasta"], 1)]).json()["id"]
    kitchen = auth_headers(Role.kitchen)

    for headers, status in [(kitchen, "in_kitchen"), (kitchen, "served"), (waiter, "paid")]:
        r = _set_status(client, headers, order_id, status)
        assert r.status_code == 200
        assert r.json()["status"] == status


def test_same_status_returns_200_without_changes(client, menu, waiter):
    order_id = _order(client, waiter, menu["table"], [(menu["pasta"], 1)]).json()["id"]

    r = _set_status(client, waiter, order_id, "pending")

    assert r.status_code == 200
    assert r.json()["status"] == "pending"


@pytest.mark.parametrize("status", ["served", "paid"])
def test_skipping_states_returns_409(client, menu, waiter, status):
    order_id = _order(client, waiter, menu["table"], [(menu["pasta"], 1)]).json()["id"]

    _assert_error(_set_status(client, waiter, order_id, status), 409, "conflict")


def test_cancelled_order_cannot_change_status(client, menu, waiter):
    order_id = _order(client, waiter, menu["table"], [(menu["pasta"], 1)]).json()["id"]
    assert _set_status(client, waiter, order_id, "cancelled").status_code == 200

    _assert_error(_set_status(client, waiter, order_id, "in_kitchen"), 409, "conflict")


def test_unknown_status_value_returns_422(client, menu, waiter):
    order_id = _order(client, waiter, menu["table"], [(menu["pasta"], 1)]).json()["id"]

    _assert_error(_set_status(client, waiter, order_id, "quemado"), 422, "validation_error")


def test_status_of_unknown_order_returns_404(client, waiter):
    _assert_error(_set_status(client, waiter, MISSING_ID, "in_kitchen"), 404, "not_found")
