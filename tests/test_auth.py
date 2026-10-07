<<<<<<< HEAD
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.jwt import create_access_token
from app.database import Base, get_db
from app.main import app
=======
from app.core.security import create_access_token
from app.models.model_user import Role
>>>>>>> 6b0efdc4fd11487e861cdc1dbb171c2f62db3472


def login(client, email, password):
    return client.post("/auth/login", data={"username": email, "password": password})

<<<<<<< HEAD
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def create_test_user():
    """Crea un usuario de prueba directamente en la BD."""
    from app.crud.crud_user import hash_password
    from app.models.model_user import User
    db = TestingSessionLocal()
    user = User(
        name="Test User",
        email="test@test.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()

def test_login_success():
    create_test_user()
    r = client.post("/auth/login", data={"username": "test@test.com", "password": "password123"})
=======
def test_login_success(client, make_user):
    make_user(Role.waiter, email="test@test.com")
    r = login(client, "test@test.com", "secreto123")
>>>>>>> 6b0efdc4fd11487e861cdc1dbb171c2f62db3472
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_token_sirve_para_me(client, make_user):
    make_user(Role.waiter, email="test@test.com")
    token = login(client, "test@test.com", "secreto123").json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "test@test.com"
    assert r.json()["role"] == "waiter"

def test_login_wrong_password(client, make_user):
    make_user(Role.waiter, email="test@test.com")
    r = login(client, "test@test.com", "wrong")
    assert r.status_code == 401

def test_login_user_not_found(client):
    r = login(client, "nobody@test.com", "pass")
    assert r.status_code == 401

def test_login_usuario_desactivado_401(client, make_user):
    make_user(Role.waiter, email="test@test.com", is_active=False)
    r = login(client, "test@test.com", "secreto123")
    assert r.status_code == 401

def test_get_me_success(client, make_user):
    user = make_user(Role.customer, email="test@test.com")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {create_access_token(user.id)}"})
    assert r.status_code == 200
    assert r.json()["email"] == "test@test.com"
    assert "password_hash" not in r.json()

def test_get_me_invalid_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer token_falso"})
    assert r.status_code == 401

def test_get_me_no_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401
