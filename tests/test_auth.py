import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.jwt import create_access_token
from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_auth.db"
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
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password():
    create_test_user()
    r = client.post("/auth/login", data={"username": "test@test.com", "password": "wrong"})
    assert r.status_code == 401

def test_login_user_not_found():
    r = client.post("/auth/login", data={"username": "nobody@test.com", "password": "pass"})
    assert r.status_code == 401

def test_get_me_success():
    create_test_user()
    token = create_access_token(data={"sub": "test@test.com"})
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "test@test.com"

def test_get_me_invalid_token():
    r = client.get("/auth/me", headers={"Authorization": "Bearer token_falso"})
    assert r.status_code == 401

def test_get_me_no_token():
    r = client.get("/auth/me")
    assert r.status_code == 401