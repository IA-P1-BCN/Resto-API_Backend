import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app, get_db
from app.database import Base

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

def user_data():
    return {
        "name": "Juan Pérez",
        "email": "juan@test.com",
        "password": "secreto123",
        "phone": "600123456"
    }

def test_create_user_success():
    r = client.post("/users/", json=user_data())
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "juan@test.com"
    assert data["is_active"] is True
    assert "password_hash" not in data

def test_create_user_duplicate_email():
    client.post("/users/", json=user_data())
    r = client.post("/users/", json=user_data())
    assert r.status_code == 409

def test_create_user_invalid_data():
    r = client.post("/users/", json={"name": "", "email": "bad"})
    assert r.status_code == 422

def test_list_users_empty():
    r = client.get("/users/")
    assert r.status_code == 200
    assert r.json() == []

def test_list_users_with_data():
    client.post("/users/", json=user_data())
    r = client.get("/users/")
    assert r.status_code == 200
    assert len(r.json()) == 1

def test_get_user_by_id():
    client.post("/users/", json=user_data())
    r = client.get("/users/1")
    assert r.status_code == 200
    assert r.json()["id"] == 1

def test_get_user_not_found():
    r = client.get("/users/999")
    assert r.status_code == 404

def test_update_user():
    client.post("/users/", json=user_data())
    r = client.put("/users/1", json={"name": "Juan Updated"})
    assert r.status_code == 200
    assert r.json()["name"] == "Juan Updated"

def test_update_user_duplicate_email():
    client.post("/users/", json=user_data())
    client.post("/users/", json={**user_data(), "email": "other@test.com"})
    r = client.put("/users/2", json={"email": "juan@test.com"})
    assert r.status_code == 409

def test_update_user_not_found():
    r = client.put("/users/999", json={"name": "X"})
    assert r.status_code == 404

def test_deactivate_user():
    client.post("/users/", json=user_data())
    r = client.patch("/users/1/deactivate")
    assert r.status_code == 200
    assert r.json()["is_active"] is False

def test_deactivate_user_not_found():
    r = client.patch("/users/999/deactivate")
    assert r.status_code == 404
