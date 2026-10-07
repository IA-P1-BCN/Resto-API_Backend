import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    client.post("/categories/", json={"name": "Entrantes", "sort_order": 1})
    client.post("/categories/", json={"name": "Postres", "sort_order": 2})
    yield
    Base.metadata.drop_all(bind=engine)

def dish_data():
    return {"category_id": 1, "name": "Patatas bravas", "price": 5.5}

def create_menu():
    client.post("/dishes/", json={"category_id": 1, "name": "Bravas", "price": 5})
    client.post("/dishes/", json={"category_id": 1, "name": "Croquetas", "price": 7})
    client.post("/dishes/", json={"category_id": 1, "name": "Jamón", "price": 15})
    client.post(
        "/dishes/",
        json={"category_id": 2, "name": "Flan", "price": 4, "is_available": False},
    )
    client.post("/dishes/", json={"category_id": 2, "name": "Helado", "price": 3})

def test_create_dish_success():
    r = client.post("/dishes/", json=dish_data())
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Patatas bravas"
    assert data["price"] == "5.50"
    assert data["is_available"] is True
    assert data["description"] is None
    assert data["id"] == 1

def test_create_dish_category_not_found():
    r = client.post("/dishes/", json={**dish_data(), "category_id": 999})
    assert r.status_code == 404

def test_create_dish_negative_price():
    r = client.post("/dishes/", json={**dish_data(), "price": -1})
    assert r.status_code == 422

def test_create_dish_too_many_decimals():
    r = client.post("/dishes/", json={**dish_data(), "price": "5.555"})
    assert r.status_code == 422

def test_list_dishes_empty():
    r = client.get("/dishes/")
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0, "page": 1, "size": 20}

def test_list_dishes_with_data():
    create_menu()
    r = client.get("/dishes/")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5

def test_filter_by_category():
    create_menu()
    r = client.get("/dishes/", params={"category_id": 2})
    data = r.json()
    assert data["total"] == 2
    assert all(d["category_id"] == 2 for d in data["items"])

def test_filter_by_availability():
    create_menu()
    r = client.get("/dishes/", params={"is_available": False})
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Flan"

def test_filter_by_max_price():
    create_menu()
    r = client.get("/dishes/", params={"max_price": 5})
    data = r.json()
    assert data["total"] == 3
    assert all(float(d["price"]) <= 5 for d in data["items"])

def test_combined_filters():
    create_menu()
    r = client.get(
        "/dishes/", params={"category_id": 1, "is_available": True, "max_price": 10}
    )
    data = r.json()
    assert data["total"] == 2
    assert [d["name"] for d in data["items"]] == ["Bravas", "Croquetas"]

def test_pagination():
    create_menu()
    r = client.get("/dishes/", params={"page": 2, "size": 2})
    data = r.json()
    assert data["total"] == 5
    assert data["page"] == 2
    assert data["size"] == 2
    assert [d["name"] for d in data["items"]] == ["Jamón", "Flan"]

def test_pagination_last_page():
    create_menu()
    r = client.get("/dishes/", params={"page": 3, "size": 2})
    data = r.json()
    assert data["total"] == 5
    assert len(data["items"]) == 1

def test_pagination_invalid_params():
    assert client.get("/dishes/", params={"page": 0}).status_code == 422
    assert client.get("/dishes/", params={"size": 101}).status_code == 422
    assert client.get("/dishes/", params={"max_price": -1}).status_code == 422

def test_get_dish_by_id():
    client.post("/dishes/", json=dish_data())
    r = client.get("/dishes/1")
    assert r.status_code == 200
    assert r.json()["name"] == "Patatas bravas"

def test_get_dish_not_found():
    r = client.get("/dishes/999")
    assert r.status_code == 404

def test_update_dish():
    client.post("/dishes/", json=dish_data())
    r = client.put("/dishes/1", json={"price": 6, "is_available": False})
    assert r.status_code == 200
    data = r.json()
    assert data["price"] == "6.00"
    assert data["is_available"] is False
    assert data["name"] == "Patatas bravas"

def test_update_dish_negative_price():
    client.post("/dishes/", json=dish_data())
    r = client.put("/dishes/1", json={"price": -3})
    assert r.status_code == 422

def test_update_dish_category_not_found():
    client.post("/dishes/", json=dish_data())
    r = client.put("/dishes/1", json={"category_id": 999})
    assert r.status_code == 404

def test_update_dish_not_found():
    r = client.put("/dishes/999", json={"name": "X"})
    assert r.status_code == 404

def test_delete_dish():
    client.post("/dishes/", json=dish_data())
    r = client.delete("/dishes/1")
    assert r.status_code == 204
    assert client.get("/dishes/1").status_code == 404

def test_delete_dish_not_found():
    r = client.delete("/dishes/999")
    assert r.status_code == 404