from app.models.dining_table import DiningTable
from app.models.model_category import Category
from app.models.model_dish import Dish


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


def test_create_order_success(client, db):
    table_id, dish_id = create_test_data(db)
    r = client.post("/orders/", json={
        "table_id": table_id,
        "items": [{"dish_id": dish_id, "quantity": 2, "notes": "sin cebolla"}]
    })
    assert r.status_code == 201
    data = r.json()
    assert float(data["total"]) == 21.00
    assert float(data["items"][0]["unit_price"]) == 10.50
    assert data["items"][0]["notes"] == "sin cebolla"


def test_create_order_dish_not_available(client, db):
    table_id, dish_id = create_test_data(db)
    dish = db.get(Dish, dish_id)
    dish.is_available = False
    db.commit()

    r = client.post("/orders/", json={
        "table_id": table_id,
        "items": [{"dish_id": dish_id, "quantity": 1}]
    })
    assert r.status_code == 409


def test_filter_orders_by_status(client, db):
    table_id, dish_id = create_test_data(db)
    client.post("/orders/", json={
        "table_id": table_id,
        "items": [{"dish_id": dish_id, "quantity": 1}]
    })
    r = client.get("/orders/?status=pending")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_kitchen_receives_order_created(client, db):
    table_id, dish_id = create_test_data(db)

    with client.websocket_connect("/ws/kitchen") as ws:
        r = client.post("/orders/", json={
            "table_id": table_id,
            "items": [{"dish_id": dish_id, "quantity": 1}]
        })
        assert r.status_code == 201

        data = ws.receive_json()
        assert data["event"] == "order_created"
        assert data["order"]["table_id"] == table_id
        assert data["order"]["status"] == "pending"


def test_kitchen_receives_status_changed(client, db):
    table_id, dish_id = create_test_data(db)

    with client.websocket_connect("/ws/kitchen") as ws:
        r = client.post("/orders/", json={
            "table_id": table_id,
            "items": [{"dish_id": dish_id, "quantity": 1}]
        })
        order_id = r.json()["id"]

        # Consumir el evento order_created
        ws.receive_json()

        # Cambiar estado
        r = client.patch(f"/orders/{order_id}/status", json={"status": "in_kitchen"})
        assert r.status_code == 200

        data = ws.receive_json()
        assert data["event"] == "order_status_changed"
        assert data["order"]["status"] == "in_kitchen"
