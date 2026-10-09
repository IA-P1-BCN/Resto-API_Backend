import pytest

from app.core.security import create_access_token
from app.models.dining_table import DiningTable
from app.models.model_category import Category
from app.models.model_dish import Dish
from app.models.model_user import Role


def create_test_data(db):
    table = DiningTable(number=1, capacity=4, location="terrace")
    category = Category(name="Principales")
    db.add(category)
    db.flush()
    dish = Dish(name="Pasta", price=10.50, is_available=True, category_id=category.id)
    db.add(table)
    db.add(dish)
    db.commit()
    return table.id, dish.id


def kitchen_ws_url(auth_headers):
    """URL del WebSocket de cocina con el token de un usuario kitchen (HU-05)."""
    token = auth_headers(Role.kitchen)["Authorization"].removeprefix("Bearer ")
    return f"/ws/kitchen?token={token}"


def new_order(client, headers, table_id, dish_id, quantity=1):
    return client.post("/orders/", headers=headers, json={
        "table_id": table_id,
        "items": [{"dish_id": dish_id, "quantity": quantity}]
    })


def test_create_order_success(client, db, auth_headers):
    table_id, dish_id = create_test_data(db)
    r = client.post("/orders/", headers=auth_headers(Role.waiter), json={
        "table_id": table_id,
        "items": [{"dish_id": dish_id, "quantity": 2, "notes": "sin cebolla"}]
    })
    assert r.status_code == 201
    data = r.json()
    assert float(data["total"]) == 21.00
    assert float(data["items"][0]["unit_price"]) == 10.50
    assert data["items"][0]["notes"] == "sin cebolla"


def test_create_order_guarda_el_camarero(client, db, make_user):
    table_id, dish_id = create_test_data(db)
    waiter = make_user(Role.waiter)
    headers = {"Authorization": f"Bearer {create_access_token(waiter.id)}"}
    r = new_order(client, headers, table_id, dish_id)
    assert r.status_code == 201
    assert r.json()["waiter_id"] == waiter.id


def test_create_order_dish_not_available(client, db, auth_headers):
    table_id, dish_id = create_test_data(db)
    dish = db.get(Dish, dish_id)
    dish.is_available = False
    db.commit()

    r = new_order(client, auth_headers(Role.waiter), table_id, dish_id)
    assert r.status_code == 409


def test_filter_orders_by_status(client, db, auth_headers):
    table_id, dish_id = create_test_data(db)
    new_order(client, auth_headers(Role.waiter), table_id, dish_id)
    r = client.get("/orders/?status=pending", headers=auth_headers(Role.waiter))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_kitchen_receives_order_created(client, db, auth_headers):
    table_id, dish_id = create_test_data(db)

    with client.websocket_connect(kitchen_ws_url(auth_headers)) as ws:
        r = new_order(client, auth_headers(Role.waiter), table_id, dish_id)
        assert r.status_code == 201

        data = ws.receive_json()
        assert data["event"] == "order_created"
        assert data["order"]["table_id"] == table_id
        assert data["order"]["status"] == "pending"


def test_kitchen_receives_status_changed(client, db, auth_headers):
    table_id, dish_id = create_test_data(db)

    with client.websocket_connect(kitchen_ws_url(auth_headers)) as ws:
        r = new_order(client, auth_headers(Role.waiter), table_id, dish_id)
        order_id = r.json()["id"]

        # Consumir el evento order_created
        ws.receive_json()

        # Cambiar estado
        r = client.patch(
            f"/orders/{order_id}/status",
            headers=auth_headers(Role.kitchen),
            json={"status": "in_kitchen"},
        )
        assert r.status_code == 200

        data = ws.receive_json()
        assert data["event"] == "order_status_changed"
        assert data["order"]["status"] == "in_kitchen"


# --- Permisos (HU-05): sala crea; sala y cocina consultan y cambian el estado ---


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("post", "/orders/"),
        ("get", "/orders/"),
        ("get", "/orders/1"),
        ("patch", "/orders/1/status"),
    ],
)
def test_orders_sin_token_401(client, method, url):
    assert client.request(method, url, json={}).status_code == 401


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("post", "/orders/"),
        ("get", "/orders/"),
        ("get", "/orders/1"),
        ("patch", "/orders/1/status"),
    ],
)
def test_orders_customer_403(client, auth_headers, method, url):
    r = client.request(method, url, headers=auth_headers(Role.customer), json={})
    assert r.status_code == 403


def test_orders_kitchen_no_crea_pedidos_403(client, db, auth_headers):
    table_id, dish_id = create_test_data(db)
    assert new_order(client, auth_headers(Role.kitchen), table_id, dish_id).status_code == 403


@pytest.mark.parametrize("role", [Role.admin, Role.waiter])
def test_orders_sala_crea_pedidos_201(client, db, auth_headers, role):
    table_id, dish_id = create_test_data(db)
    assert new_order(client, auth_headers(role), table_id, dish_id).status_code == 201


@pytest.mark.parametrize("role", [Role.admin, Role.waiter, Role.kitchen])
def test_orders_sala_y_cocina_consultan_y_cambian_estado(client, db, auth_headers, role):
    table_id, dish_id = create_test_data(db)
    order_id = new_order(client, auth_headers(Role.waiter), table_id, dish_id).json()["id"]
    headers = auth_headers(role)

    assert client.get("/orders/", headers=headers).status_code == 200
    assert client.get(f"/orders/{order_id}", headers=headers).status_code == 200
    r = client.patch(f"/orders/{order_id}/status", headers=headers, json={"status": "in_kitchen"})
    assert r.status_code == 200
    assert r.json()["status"] == "in_kitchen"
