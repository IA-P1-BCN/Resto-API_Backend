from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException

from app.config import settings
from app.core.permissions import ensure_owner_or_role
from app.core.security import create_access_token, decode_access_token
from app.models.model_user import Role
from app.scripts.create_admin import create_admin


def test_users_sin_token_401(client):
    r = client.get("/users/")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"

def test_users_token_invalido_401(client):
    r = client.get("/users/", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert r.status_code == 401

def test_users_token_caducado_401(client, make_user):
    user = make_user(Role.admin)
    expired = jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    r = client.get("/users/", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401

def test_users_usuario_desactivado_401(client, make_user):
    user = make_user(Role.admin, is_active=False)
    r = client.get("/users/", headers={"Authorization": f"Bearer {create_access_token(user.id)}"})
    assert r.status_code == 401

def test_users_usuario_inexistente_401(client):
    r = client.get("/users/", headers={"Authorization": f"Bearer {create_access_token(999)}"})
    assert r.status_code == 401

@pytest.mark.parametrize("role", [Role.waiter, Role.kitchen, Role.customer])
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
def test_users_solo_admin_403(client, auth_headers, role, method, url):
    r = client.request(method, url, headers=auth_headers(role), json={})
    assert r.status_code == 403

def test_users_admin_200(client, admin_headers):
    r = client.get("/users/", headers=admin_headers)
    assert r.status_code == 200

def test_token_ida_y_vuelta():
    assert decode_access_token(create_access_token(42)) == 42

def test_customer_ve_sus_reservas(make_user):
    customer = make_user(Role.customer)
    ensure_owner_or_role(customer, customer.id, Role.admin, Role.waiter)

def test_customer_no_ve_reservas_ajenas_403(make_user):
    customer = make_user(Role.customer)
    with pytest.raises(HTTPException) as exc:
        ensure_owner_or_role(customer, customer.id + 1, Role.admin, Role.waiter)
    assert exc.value.status_code == 403

@pytest.mark.parametrize("role", [Role.admin, Role.waiter])
def test_personal_ve_reservas_ajenas(make_user, role):
    staff = make_user(role)
    ensure_owner_or_role(staff, staff.id + 1, Role.admin, Role.waiter)

def test_create_admin(db):
    user = create_admin(db, "jefa@test.com", "secreto123", "Jefa")
    assert user.role == "admin"
    assert create_admin(db, "jefa@test.com", "otra").id == user.id

def test_create_admin_promociona_existente(db, make_user):
    customer = make_user(Role.customer, email="cliente@test.com", is_active=False)
    user = create_admin(db, "cliente@test.com", "secreto123")
    assert user.id == customer.id
    assert user.role == "admin"
    assert user.is_active is True
