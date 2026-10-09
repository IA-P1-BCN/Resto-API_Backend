"""Tests de integración de login y permisos por rol (HU-04 y HU-05).

Complementan tests/test_auth.py y tests/test_permissions.py: aquí se recorre el
flujo real login → token → endpoint protegido y se comprueba siempre el formato
común de error {"detail", "code"}.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest

from app.config import settings
from app.core.security import create_access_token, decode_access_token
from app.models.dining_table import DiningTable
from app.models.model_user import Role
from app.models.reservation import Reservation

PASSWORD = "secreto123"


def _login(client, email: str, password: str = PASSWORD):
    return client.post("/auth/login", data={"username": email, "password": password})


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _assert_error(response: Any, status_code: int, code: str) -> None:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["code"] == code


def test_login_ok_returns_200_and_token_of_the_user(client, make_user):
    user = make_user(Role.waiter, email="camarero@test.com")

    r = _login(client, "camarero@test.com")

    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert decode_access_token(body["access_token"]) == user.id


def test_login_token_gives_access_to_protected_endpoint(client, make_user):
    make_user(Role.admin, email="admin@test.com")
    token = _login(client, "admin@test.com").json()["access_token"]

    r = client.get("/users/", headers=_bearer(token))

    assert r.status_code == 200


def test_login_wrong_password_returns_401_with_error_format(client, make_user):
    make_user(Role.waiter, email="camarero@test.com")

    r = _login(client, "camarero@test.com", "incorrecta")

    _assert_error(r, 401, "unauthorized")
    assert r.headers["www-authenticate"] == "Bearer"
    assert "access_token" not in r.json()


def test_login_unknown_email_returns_401_with_error_format(client):
    _assert_error(_login(client, "nadie@test.com"), 401, "unauthorized")


def test_login_without_password_returns_422(client):
    r = client.post("/auth/login", data={"username": "nadie@test.com"})

    _assert_error(r, 422, "validation_error")


def test_expired_token_returns_401_with_error_format(client, make_user):
    user = make_user(Role.waiter)
    expired = jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(UTC) - timedelta(seconds=1)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    r = client.get("/auth/me", headers=_bearer(expired))

    _assert_error(r, 401, "unauthorized")
    assert r.headers["www-authenticate"] == "Bearer"


def test_token_signed_with_another_key_returns_401(client, make_user):
    user = make_user(Role.admin)
    forged = jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "otra-clave-que-no-es-la-del-servidor-000000",
        algorithm=settings.JWT_ALGORITHM,
    )

    _assert_error(client.get("/users/", headers=_bearer(forged)), 401, "unauthorized")


def test_changed_password_works_and_old_one_returns_401(client, make_user, admin_headers):
    user = make_user(Role.waiter, email="camarero@test.com")

    r = client.put(f"/users/{user.id}", headers=admin_headers, json={"password": "nueva-clave-1"})

    assert r.status_code == 200
    assert _login(client, "camarero@test.com", "nueva-clave-1").status_code == 200
    _assert_error(_login(client, "camarero@test.com"), 401, "unauthorized")


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/users/"),
        ("post", "/users/"),
        ("get", "/users/1"),
        ("put", "/users/1"),
        ("patch", "/users/1/deactivate"),
    ],
)
def test_waiter_accessing_users_returns_403_with_error_format(client, make_user, method, url):
    make_user(Role.waiter, email="camarero@test.com")
    token = _login(client, "camarero@test.com").json()["access_token"]

    r = client.request(method, url, headers=_bearer(token), json={})

    _assert_error(r, 403, "forbidden")


def test_customer_gets_other_customer_reservation_returns_403(client, db, make_user):
    owner = make_user(Role.customer, email="duena@test.com")
    other = make_user(Role.customer, email="otra@test.com")
    table = DiningTable(number=1, capacity=4, location="indoor")
    db.add(table)
    db.flush()
    reservation = Reservation(
        user_id=owner.id,
        table_id=table.id,
        reserved_at=datetime.fromisoformat("2026-10-10T20:00"),
        duration_min=90,
        party_size=2,
    )
    db.add(reservation)
    db.commit()

    own = client.get(f"/reservations/{reservation.id}", headers=_bearer(create_access_token(owner.id)))
    alien = client.get(f"/reservations/{reservation.id}", headers=_bearer(create_access_token(other.id)))

    assert own.status_code == 200
    assert alien.status_code == 403
    assert isinstance(alien.json()["detail"], str)
    assert alien.json()["code"]
