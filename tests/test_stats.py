"""Estadísticas: ventas, platos más vendidos, caché y permisos (HU-15)."""

from datetime import date, datetime
from decimal import Decimal
from time import monotonic

import pytest

from app.models.dining_table import DiningTable
from app.models.model_category import Category
from app.models.model_dish import Dish
from app.models.model_order import Order
from app.models.model_order_item import OrderItem
from app.models.model_user import Role
from app.services import stats

PRICES = {
    "paella": Decimal("14.00"),
    "croquetas": Decimal("6.50"),
    "flan": Decimal("4.00"),
}


@pytest.fixture(autouse=True)
def empty_cache():
    """La caché vive en memoria y sobrevive entre tests: se vacía antes y después."""
    stats.clear_cache()
    yield
    stats.clear_cache()


@pytest.fixture
def dishes(db):
    """Crea los platos de PRICES y devuelve {nombre: id}."""
    category = Category(name="Main")
    db.add(category)
    db.flush()
    ids = {}
    for name, price in PRICES.items():
        dish = Dish(category_id=category.id, name=name, price=price)
        db.add(dish)
        db.flush()
        ids[name] = dish.id
    db.commit()
    return ids


@pytest.fixture
def make_order(db, dishes):
    """Crea un pedido con sus líneas: make_order("2026-10-01", "paid", paella=2).

    El total del pedido es la suma de las líneas con los precios de PRICES.
    """
    counter = {"table": 0}

    def _make(day: str, status: str = "paid", **lines: int) -> Order:
        counter["table"] += 1
        table = DiningTable(
            number=counter["table"], capacity=4, location="terrace")
        db.add(table)
        db.flush()
        order = Order(
            table_id=table.id,
            status=status,
            total=sum((PRICES[name] * qty for name,
                      qty in lines.items()), Decimal(0)),
            created_at=datetime.fromisoformat(f"{day}T13:30:00"),
        )
        order.items = [
            OrderItem(dish_id=dishes[name],
                      quantity=qty, unit_price=PRICES[name])
            for name, qty in lines.items()
        ]
        db.add(order)
        db.commit()
        return order

    return _make


def test_sales_without_orders_are_zero(db):
    summary = stats.sales_summary(db)

    assert summary.orders_count == 0
    assert summary.total_sales == Decimal("0.00")
    assert summary.average_ticket == Decimal("0.00")
    assert summary.daily == ()


def test_sales_totals_and_average_ticket(db, make_order):
    make_order("2026-10-01", "paid", paella=2)
    make_order("2026-10-01", "served", croquetas=1, flan=1)
    make_order("2026-10-02", "paid", flan=1)

    summary = stats.sales_summary(db)

    assert summary.orders_count == 3
    assert summary.total_sales == Decimal("42.50")
    assert summary.average_ticket == Decimal("14.17")


def test_sales_daily_breakdown_is_ordered_by_day(db, make_order):
    make_order("2026-10-02", "paid", flan=1)
    make_order("2026-10-01", "paid", paella=1)
    make_order("2026-10-01", "paid", croquetas=2)

    daily = stats.sales_summary(db).daily

    assert [(d.day, d.orders_count, d.total_sales) for d in daily] == [
        (date(2026, 10, 1), 2, Decimal("27.00")),
        (date(2026, 10, 2), 1, Decimal("4.00")),
    ]


@pytest.mark.parametrize("status", ["pending", "in_kitchen", "cancelled"])
def test_sales_ignore_orders_that_are_not_sales(db, make_order, status):
    make_order("2026-10-01", "paid", flan=1)
    make_order("2026-10-01", status, paella=5)

    summary = stats.sales_summary(db)

    assert summary.orders_count == 1
    assert summary.total_sales == Decimal("4.00")


def test_sales_date_range_includes_both_ends(db, make_order):
    make_order("2026-09-30", "paid", paella=1)
    make_order("2026-10-01", "paid", croquetas=1)
    make_order("2026-10-03", "paid", flan=1)
    make_order("2026-10-04", "paid", paella=1)

    summary = stats.sales_summary(db, date(2026, 10, 1), date(2026, 10, 3))

    assert summary.orders_count == 2
    assert summary.total_sales == Decimal("10.50")


def test_sales_with_only_one_date_limit(db, make_order):
    make_order("2026-09-30", "paid", paella=1)
    make_order("2026-10-01", "paid", flan=1)

    assert stats.sales_summary(
        db, date_from=date(2026, 10, 1)).orders_count == 1
    assert stats.sales_summary(db, date_to=date(2026, 9, 30)).orders_count == 1


def test_top_dishes_ordered_by_quantity(db, make_order):
    make_order("2026-10-01", "paid", paella=1, croquetas=3)
    make_order("2026-10-02", "served", croquetas=2, flan=4)

    top = stats.top_dishes(db)

    assert [(d.name, d.quantity, d.revenue) for d in top] == [
        ("croquetas", 5, Decimal("32.50")),
        ("flan", 4, Decimal("16.00")),
        ("paella", 1, Decimal("14.00")),
    ]


def test_top_dishes_tie_goes_to_higher_revenue(db, make_order):
    make_order("2026-10-01", "paid", flan=2, paella=2)

    assert [d.name for d in stats.top_dishes(db)] == ["paella", "flan"]


def test_top_dishes_revenue_uses_price_at_order_time(db, make_order, dishes):
    make_order("2026-10-01", "paid", paella=2)
    db.get(Dish, dishes["paella"]).price = Decimal(
        "99.00")
    db.commit()

    assert stats.top_dishes(db)[0].revenue == Decimal("28.00")


def test_top_dishes_respects_limit(db, make_order):
    make_order("2026-10-01", "paid", paella=3, croquetas=2, flan=1)

    assert [d.name for d in stats.top_dishes(db, limit=2)] == [
        "paella", "croquetas"]


def test_top_dishes_ignore_orders_that_are_not_sales(db, make_order):
    make_order("2026-10-01", "paid", flan=1)
    make_order("2026-10-01", "cancelled", paella=10)
    make_order("2026-10-01", "pending", croquetas=10)

    assert [(d.name, d.quantity)
            for d in stats.top_dishes(db)] == [("flan", 1)]


def test_top_dishes_filtered_by_date(db, make_order):
    make_order("2026-09-30", "paid", paella=10)
    make_order("2026-10-01", "paid", flan=1)

    top = stats.top_dishes(db, date(2026, 10, 1), date(2026, 10, 1))

    assert [d.name for d in top] == ["flan"]


def test_top_dishes_without_sales_is_empty(db, dishes):
    assert stats.top_dishes(db) == ()


def test_get_sales(client, admin_headers, make_order):
    make_order("2026-10-01", "paid", paella=2)

    r = client.get(
        "/stats/sales",
        params={"from": "2026-10-01", "to": "2026-10-01"},
        headers=admin_headers,
    )

    assert r.status_code == 200
    assert r.json() == {
        "date_from": "2026-10-01",
        "date_to": "2026-10-01",
        "orders_count": 1,
        "total_sales": "28.00",
        "average_ticket": "28.00",
        "daily": [{"day": "2026-10-01", "orders_count": 1, "total_sales": "28.00"}],
    }


def test_get_sales_without_filters_and_without_orders(client, admin_headers):
    r = client.get("/stats/sales", headers=admin_headers)

    assert r.status_code == 200
    assert r.json()["date_from"] is None
    assert r.json()["total_sales"] == "0.00"


def test_get_sales_from_after_to_is_422(client, admin_headers):
    r = client.get(
        "/stats/sales",
        params={"from": "2026-10-02", "to": "2026-10-01"},
        headers=admin_headers,
    )

    assert r.status_code == 422
    assert r.json()["code"] == "invalid_date_range"


def test_get_sales_invalid_date_is_validation_error(client, admin_headers):
    r = client.get(
        "/stats/sales", params={"from": "yesterday"}, headers=admin_headers)

    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"


def test_get_top_dishes(client, admin_headers, make_order, dishes):
    make_order("2026-10-01", "paid", paella=1, croquetas=3)

    r = client.get("/stats/top-dishes", headers=admin_headers)

    assert r.status_code == 200
    assert r.json() == [
        {
            "dish_id": dishes["croquetas"],
            "name": "croquetas",
            "quantity": 3,
            "revenue": "19.50",
        },
        {"dish_id": dishes["paella"], "name": "paella",
            "quantity": 1, "revenue": "14.00"},
    ]


def test_get_top_dishes_default_limit_is_5(client, admin_headers, db, make_order, dishes):
    category_id = db.get(Dish, dishes["flan"]).category_id
    order = make_order("2026-10-01", "paid")
    for i in range(1, 7):
        dish = Dish(category_id=category_id,
                    name=f"dish {i}", price=Decimal("1.00"))
        db.add(dish)
        db.flush()
        order.items.append(
            OrderItem(dish_id=dish.id, quantity=i, unit_price=dish.price))
    db.commit()

    r = client.get("/stats/top-dishes", headers=admin_headers)

    assert [d["name"]
            for d in r.json()] == [f"dish {i}" for i in (6, 5, 4, 3, 2)]


def test_get_top_dishes_limit(client, admin_headers, make_order):
    make_order("2026-10-01", "paid", paella=3, flan=1)

    r = client.get("/stats/top-dishes",
                   params={"limit": 1}, headers=admin_headers)

    assert [d["name"] for d in r.json()] == ["paella"]


@pytest.mark.parametrize("limit", [0, 51, "five"])
def test_get_top_dishes_invalid_limit_is_422(client, admin_headers, limit):
    r = client.get("/stats/top-dishes",
                   params={"limit": limit}, headers=admin_headers)

    assert r.status_code == 422
    assert r.json()["code"] == "validation_error"


def test_get_top_dishes_from_after_to_is_422(client, admin_headers):
    r = client.get(
        "/stats/top-dishes",
        params={"from": "2026-10-02", "to": "2026-10-01"},
        headers=admin_headers,
    )

    assert r.status_code == 422
    assert r.json()["code"] == "invalid_date_range"


def test_sales_are_cached_until_cache_is_cleared(client, admin_headers, make_order):
    make_order("2026-10-01", "paid", flan=1)
    first = client.get("/stats/sales", headers=admin_headers).json()

    make_order("2026-10-01", "paid", paella=1)
    cached = client.get("/stats/sales", headers=admin_headers).json()
    stats.clear_cache()
    fresh = client.get("/stats/sales", headers=admin_headers).json()

    assert cached == first
    assert fresh["orders_count"] == 2


def test_sales_cache_expires_after_ttl(client, admin_headers, make_order):
    make_order("2026-10-01", "paid", flan=1)
    client.get("/stats/sales", headers=admin_headers)
    make_order("2026-10-01", "paid", paella=1)

    stats._sales_cache.expire(monotonic() + stats.settings.STATS_CACHE_TTL + 1)

    assert client.get(
        "/stats/sales", headers=admin_headers).json()["orders_count"] == 2


def test_sales_cache_key_depends_on_dates(client, admin_headers, make_order):
    make_order("2026-09-30", "paid", flan=1)
    make_order("2026-10-01", "paid", paella=1)

    all_days = client.get("/stats/sales", headers=admin_headers).json()
    one_day = client.get(
        "/stats/sales", params={"from": "2026-10-01"}, headers=admin_headers
    ).json()

    assert all_days["orders_count"] == 2
    assert one_day["orders_count"] == 1


def test_top_dishes_are_cached(client, admin_headers, make_order):
    make_order("2026-10-01", "paid", flan=1)
    first = client.get("/stats/top-dishes", headers=admin_headers).json()

    make_order("2026-10-01", "paid", paella=5)

    assert client.get("/stats/top-dishes",
                      headers=admin_headers).json() == first


def test_top_dishes_cache_key_depends_on_limit(client, admin_headers, make_order):
    make_order("2026-10-01", "paid", flan=1, paella=2)

    one = client.get("/stats/top-dishes",
                     params={"limit": 1}, headers=admin_headers)
    two = client.get("/stats/top-dishes",
                     params={"limit": 2}, headers=admin_headers)

    assert len(one.json()) == 1
    assert len(two.json()) == 2


@pytest.mark.parametrize("path", ["/stats/sales", "/stats/top-dishes"])
@pytest.mark.parametrize("role", [Role.waiter, Role.kitchen, Role.customer])
def test_only_admin_can_see_stats(client, auth_headers, path, role):
    r = client.get(path, headers=auth_headers(role))

    assert r.status_code == 403


@pytest.mark.parametrize("path", ["/stats/sales", "/stats/top-dishes"])
def test_stats_without_token_is_401(client, path):
    assert client.get(path).status_code == 401
