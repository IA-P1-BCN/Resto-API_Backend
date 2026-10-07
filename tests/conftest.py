"""Shared pytest fixtures (L-02 · HU-09 / HU-17).

Mientras el esqueleto de Carla (app/main.py, app/core/*, modelos User y Role)
no esté en dev, las fixtures que dependen de él hacen pytest.skip en vez de
romper la recolección. Cada suposición va marcada con ASSUMPTION y está
listada en PENDING-CONTRACTS.md.

BD de test: se usa TEST_DATABASE_URL si existe. Si no, DATABASE_URL solo cuando
ENVIRONMENT=test viene ya definido (como en CI), para no tocar nunca la BD de
desarrollo por accidente.
"""

import importlib
import os
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from types import ModuleType
from typing import Any

import bcrypt
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# Se lee antes de los setdefault de abajo: solo CI (o quien lo exporte) activa DATABASE_URL.
_ENVIRONMENT_IS_TEST = os.getenv("ENVIRONMENT") == "test"

# Valores por defecto para que pydantic-settings no falle al importar la app.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "pytest-only-secret-key-not-for-production")
os.environ.setdefault("EMAIL_ENABLED", "false")

# ASSUMPTION: nombres de rol de la tabla roles (plan §3.1) — Carla, C-01/C-03.
ROLE_NAMES = ("admin", "waiter", "kitchen", "customer")
TEST_PASSWORD = "Test-Password-123"

# TODO(L-02): poner a False cuando Carla mergee POST /auth/login (C-03).
# Con True, los tokens se firman aquí (stub) en vez de pedirlos al endpoint de login.
USE_STUB_TOKENS = True
# ASSUMPTION: algoritmo JWT HS256 firmado con JWT_SECRET_KEY — Carla, C-03.
JWT_ALGORITHM = "HS256"


def _test_database_url() -> str | None:
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return explicit
    if _ENVIRONMENT_IS_TEST:
        return os.getenv("DATABASE_URL")
    return None


def _is_missing(module: str, exc: ModuleNotFoundError) -> bool:
    """True si falta el propio módulo (o un paquete padre), no una dependencia suya."""
    return exc.name is not None and (
        module == exc.name or module.startswith(f"{exc.name}.")
    )


def _import_or_skip(module: str, owner: str) -> ModuleType:
    try:
        return importlib.import_module(module)
    except ModuleNotFoundError as exc:
        if _is_missing(module, exc):
            pytest.skip(f"{module} todavía no existe (depende de {owner})")
        raise


def _import_optional(module: str) -> ModuleType | None:
    try:
        return importlib.import_module(module)
    except ModuleNotFoundError as exc:
        if _is_missing(module, exc):
            return None
        raise


# --- Base de datos ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = _test_database_url()
    if url is None:
        pytest.skip(
            "Sin BD de test: define TEST_DATABASE_URL (o ENVIRONMENT=test + DATABASE_URL, como en CI)"
        )

    # ASSUMPTION: app.core.database expone `Base` — Carla, C-01.
    database = _import_or_skip("app.core.database", "Carla")
    # Registrar en Base.metadata los modelos que ya existan antes de create_all.
    # ASSUMPTION: modelos User y Role en app/models/user.py y app/models/role.py (un fichero por tabla).
    _import_optional("app.models")
    _import_optional("app.models.role")
    _import_optional("app.models.user")
    importlib.import_module("app.models.dining_table")

    test_engine = create_engine(url, pool_pre_ping=True)
    # create_all es idempotente: en CI el esquema ya lo ha creado `alembic upgrade head`.
    # No se hace drop_all para no pisar la tabla alembic_version.
    database.Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """Sesión por test dentro de una transacción que se deshace al final.

    Con join_transaction_mode="create_savepoint", los session.commit() de los
    servicios solo cierran un SAVEPOINT y el rollback final lo borra todo.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# --- Cliente HTTP ----------------------------------------------------------------------------


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """TestClient sobre app.main:app con get_db apuntando a la sesión del test."""
    # ASSUMPTION: app.main expone `app` (FastAPI) — Carla, C-01.
    main = _import_or_skip("app.main", "Carla")
    # ASSUMPTION: app.core.database expone la dependencia `get_db` — Carla, C-01.
    database = _import_or_skip("app.core.database", "Carla")
    app = main.app

    def _override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[database.get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


# --- Usuarios y tokens -----------------------------------------------------------------------


@pytest.fixture
def create_user(db: Session) -> Callable[..., Any]:
    """Factory: create_user("waiter") crea (o reutiliza) el rol y un usuario activo."""
    # ASSUMPTION: Role(id, name, description) y User(id, name, email, password_hash, phone,
    # role_id, is_active), según plan §3.1 — Carla, C-01.
    role_model = _import_or_skip("app.models.role", "Carla").Role
    user_model = _import_or_skip("app.models.user", "Carla").User

    def _create(role_name: str, email: str | None = None) -> Any:
        if role_name not in ROLE_NAMES:
            raise ValueError(f"Rol desconocido: {role_name!r}. Válidos: {ROLE_NAMES}")

        # Los roles pueden venir sembrados por la migración (C-03): get-or-create.
        role = db.scalar(select(role_model).where(role_model.name == role_name))
        if role is None:
            role = role_model(name=role_name)
            db.add(role)
            db.flush()

        # ASSUMPTION: password_hash es bcrypt (hashpw/checkpw) — Carla, C-02.
        password_hash = bcrypt.hashpw(
            TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)
        ).decode()
        user = user_model(
            name=f"Test {role_name}",
            email=email or f"{role_name}-{uuid.uuid4().hex[:8]}@test.restoapi.dev",
            password_hash=password_hash,
            role_id=role.id,
            is_active=True,
        )
        db.add(user)
        db.flush()
        return user

    return _create


def _stub_token(user: Any, role_name: str) -> str:
    # TODO(L-02): stub hasta que exista /auth/login. Borrar cuando USE_STUB_TOKENS sea False.
    # ASSUMPTION: claims del JWT real = sub (id del usuario como str), role y exp — Carla, C-03.
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "role": role_name,
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    return jwt.encode(payload, os.environ["JWT_SECRET_KEY"], algorithm=JWT_ALGORITHM)


def _login_token(client: TestClient, email: str) -> str:
    # ASSUMPTION: POST /auth/login con JSON {"email", "password"} devuelve
    # {"access_token": str, "token_type": "bearer"} — Carla, C-03.
    response = client.post(
        "/auth/login", json={"email": email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login de test fallido: {response.text}"
    body = response.json()
    assert body["token_type"] == "bearer"
    return body["access_token"]


@pytest.fixture
def auth_headers(
    create_user: Callable[..., Any], request: pytest.FixtureRequest
) -> Callable[[str], dict[str, str]]:
    """Factory: auth_headers("admin") -> {"Authorization": "Bearer <token>"}.

    Un usuario por rol y test; las llamadas repetidas con el mismo rol reutilizan el token.
    """
    cache: dict[str, dict[str, str]] = {}

    def _headers(role_name: str) -> dict[str, str]:
        if role_name not in cache:
            user = create_user(role_name)
            if USE_STUB_TOKENS:
                token = _stub_token(user, role_name)
            else:
                token = _login_token(request.getfixturevalue("client"), user.email)
            cache[role_name] = {"Authorization": f"Bearer {token}"}
        return cache[role_name]

    return _headers


def _token_from(headers: dict[str, str]) -> str:
    return headers["Authorization"].removeprefix("Bearer ")


@pytest.fixture
def admin_token(auth_headers: Callable[[str], dict[str, str]]) -> str:
    return _token_from(auth_headers("admin"))


@pytest.fixture
def waiter_token(auth_headers: Callable[[str], dict[str, str]]) -> str:
    return _token_from(auth_headers("waiter"))


@pytest.fixture
def customer_token(auth_headers: Callable[[str], dict[str, str]]) -> str:
    return _token_from(auth_headers("customer"))
