"""Fixtures compartidas de los tests.

Todos los tests usan la misma BD SQLite en memoria, que se crea y se borra en cada
test. El override de get_db se pone y se quita dentro de un fixture: así ningún
fichero de tests pisa los overrides de otro.
"""

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.model_user import Role, User

# StaticPool: una sola conexión, para que todas las sesiones vean la misma BD en memoria.
engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def make_user(db):
    """Crea un usuario con el rol indicado directamente en la BD."""
    def _make(role: Role | str, email: str | None = None, is_active: bool = True) -> User:
        role = Role(role)
        user = User(
            name=f"{role.value} test",
            email=email or f"{role.value}@test.com",
            # rounds=4: hash válido para verify_password pero mucho más rápido.
            password_hash=bcrypt.hashpw(b"secreto123", bcrypt.gensalt(rounds=4)).decode(),
            role=role.value,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    return _make


@pytest.fixture
def auth_headers(make_user):
    """Factory: auth_headers(Role.waiter) -> cabecera Authorization de un usuario de ese rol.

    Un usuario por rol y test: las llamadas repetidas con el mismo rol lo reutilizan.
    """
    cache: dict[Role, dict[str, str]] = {}

    def _headers(role: Role | str) -> dict[str, str]:
        role = Role(role)
        if role not in cache:
            user = make_user(role)
            cache[role] = {"Authorization": f"Bearer {create_access_token(user.id)}"}
        return cache[role]
    return _headers


@pytest.fixture
def admin_headers(auth_headers):
    return auth_headers(Role.admin)


def _token(headers: dict[str, str]) -> str:
    return headers["Authorization"].removeprefix("Bearer ")


@pytest.fixture
def admin_token(auth_headers) -> str:
    return _token(auth_headers(Role.admin))


@pytest.fixture
def waiter_token(auth_headers) -> str:
    return _token(auth_headers(Role.waiter))


@pytest.fixture
def customer_token(auth_headers) -> str:
    return _token(auth_headers(Role.customer))
