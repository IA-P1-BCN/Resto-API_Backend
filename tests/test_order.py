import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_orders.db"
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

def create_test_data():
    from app.models.dining_table import DiningTable
    from app.models.model_category import Category
    from app.models.model_dish import Dish
    db = TestingSessionLocal()
    table = DiningTable(number=1, capacity=4, location="terrace")
    category = Category(name="Principales")
    db.add(category)
    db.flush()
    dish = Dish(name="Pasta", price=10.50, is_available=True, category_id=category.id)
    db.add(table)
    db.add(dish)
    db.commit()
    table_id = table.id
    dish_id = dish.id
    db.close()
    return table_id, dish_id

def test_create_order_success():
    table_id, dish_id = create_test_data()
    r = client.post("/orders/", json={
        "table_id": table_id,
        "items": [{"dish_id": dish_id, "quantity": 2, "notes": "sin cebolla"}]
    })
    assert r.status_code == 201
    data = r.json()
    assert float(data["total"]) == 21.00
    assert float(data["items"][0]["unit_price"]) == 10.50
    assert data["items"][0]["notes"] == "sin cebolla"

def test_create_order_dish_not_available():
    table_id, dish_id = create_test_data()
    from app.models.model_dish import Dish
    db = TestingSessionLocal()
    dish = db.query(Dish).filter(Dish.id == dish_id).first()
    dish.is_available = False
    db.commit()
    db.close()

    r = client.post("/orders/", json={
        "table_id": table_id,
        "items": [{"dish_id": dish_id, "quantity": 1}]
    })
    assert r.status_code == 409

def test_filter_orders_by_status():
    table_id, dish_id = create_test_data()
    client.post("/orders/", json={
        "table_id": table_id,
        "items": [{"dish_id": dish_id, "quantity": 1}]
    })
    r = client.get("/orders/?status=pending")
    assert r.status_code == 200
    assert len(r.json()) == 1