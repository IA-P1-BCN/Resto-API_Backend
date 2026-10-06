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
    yield
    Base.metadata.drop_all(bind=engine)

def category_data():
    return {"name": "Postres", "sort_order": 3}

def test_create_category_success():
    r = client.post("/categories/", json=category_data())
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Postres"
    assert data["sort_order"] == 3
    assert data["id"] == 1

def test_create_category_default_sort_order():
    r = client.post("/categories/", json={"name": "Entrantes"})
    assert r.status_code == 201
    assert r.json()["sort_order"] == 0

def test_create_category_duplicate_name():
    client.post("/categories/", json=category_data())
    r = client.post("/categories/", json=category_data())
    assert r.status_code == 409

def test_create_category_invalid_data():
    r = client.post("/categories/", json={"name": "x" * 51})
    assert r.status_code == 422

def test_list_categories_empty():
    r = client.get("/categories/")
    assert r.status_code == 200
    assert r.json() == []

def test_list_categories_ordered_by_sort_order():
    client.post("/categories/", json={"name": "Postres", "sort_order": 3})
    client.post("/categories/", json={"name": "Entrantes", "sort_order": 1})
    r = client.get("/categories/")
    assert r.status_code == 200
    assert [c["name"] for c in r.json()] == ["Entrantes", "Postres"]

def test_get_category_by_id():
    client.post("/categories/", json=category_data())
    r = client.get("/categories/1")
    assert r.status_code == 200
    assert r.json()["name"] == "Postres"

def test_get_category_not_found():
    r = client.get("/categories/999")
    assert r.status_code == 404

def test_update_category():
    client.post("/categories/", json=category_data())
    r = client.put("/categories/1", json={"sort_order": 5})
    assert r.status_code == 200
    assert r.json()["sort_order"] == 5
    assert r.json()["name"] == "Postres"

def test_update_category_duplicate_name():
    client.post("/categories/", json=category_data())
    client.post("/categories/", json={"name": "Entrantes"})
    r = client.put("/categories/2", json={"name": "Postres"})
    assert r.status_code == 409

def test_update_category_not_found():
    r = client.put("/categories/999", json={"name": "X"})
    assert r.status_code == 404

def test_delete_category():
    client.post("/categories/", json=category_data())
    r = client.delete("/categories/1")
    assert r.status_code == 204
    assert client.get("/categories/1").status_code == 404

def test_delete_category_not_found():
    r = client.delete("/categories/999")
    assert r.status_code == 404

def test_delete_category_with_dishes():
    client.post("/categories/", json=category_data())
    client.post("/dishes/", json={"category_id": 1, "name": "Flan", "price": 4.5})
    r = client.delete("/categories/1")
    assert r.status_code == 409