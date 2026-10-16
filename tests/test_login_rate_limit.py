"""HU-31 / R-10: límite de intentos de `POST /auth/login` (integración)."""

import logging
from datetime import UTC, datetime, timedelta

import pyotp
import pytest

from app.config import settings
from app.core.exceptions import ErrorResponse
from app.models.model_user import Role

EMAIL = "ana@test.com"
PASSWORD = "secreto123"
WINDOW_SECONDS = settings.LOGIN_WINDOW_MINUTES * 60
MAX_ATTEMPTS = settings.LOGIN_MAX_ATTEMPTS


def login(client, email=EMAIL, password=PASSWORD, headers=None):
    return client.post(
        "/auth/login", data={"username": email, "password": password}, headers=headers
    )


def fail(client, times, email=EMAIL, headers=None):
    for _ in range(times):
        assert login(client, email, "incorrecta", headers).status_code == 401


@pytest.fixture
def ana(make_user):
    return make_user(Role.customer, email=EMAIL)


@pytest.fixture
def ip_header(monkeypatch):
    monkeypatch.setattr(settings, "CLIENT_IP_HEADER", "True-Client-IP")
    return "True-Client-IP"


def test_cinco_fallos_dan_401_y_el_sexto_429(client, ana):
    fail(client, MAX_ATTEMPTS)

    response = login(client, password="incorrecta")

    assert response.status_code == 429
    body = ErrorResponse.model_validate(response.json())
    assert body.code == "too_many_attempts"
    assert body.detail == "Too many failed login attempts. Try again later."
    assert 1 <= int(response.headers["Retry-After"]) <= WINDOW_SECONDS


def test_durante_el_bloqueo_la_contrasena_correcta_tambien_da_429(client, ana):
    fail(client, MAX_ATTEMPTS)

    assert login(client).status_code == 429


def test_un_login_correcto_borra_los_fallos(client, ana):
    fail(client, MAX_ATTEMPTS - 1)
    assert login(client).status_code == 200

    fail(client, MAX_ATTEMPTS)

    assert login(client).status_code == 429


def test_otro_email_desde_la_misma_ip_no_esta_bloqueado(client, ana, make_user):
    make_user(Role.waiter, email="otra@test.com")
    fail(client, MAX_ATTEMPTS)

    assert login(client, email="otra@test.com").status_code == 200


def test_el_mismo_email_desde_otra_ip_no_esta_bloqueado(client, ana, ip_header):
    fail(client, MAX_ATTEMPTS, headers={ip_header: "203.0.113.7"})

    assert login(client, headers={ip_header: "203.0.113.7"}).status_code == 429
    assert login(client, headers={ip_header: "198.51.100.1"}).status_code == 200


def test_x_forwarded_for_no_cambia_la_ip(client, ana, ip_header):
    fail(client, MAX_ATTEMPTS, headers={ip_header: "203.0.113.7"})

    response = login(
        client, headers={ip_header: "203.0.113.7", "X-Forwarded-For": "198.51.100.1"}
    )

    assert response.status_code == 429


def test_sin_cabecera_configurada_se_ignoran_las_cabeceras_del_cliente(client, ana):
    fail(client, MAX_ATTEMPTS, headers={"True-Client-IP": "203.0.113.7"})

    assert login(client, headers={"True-Client-IP": "198.51.100.1"}).status_code == 429


def test_el_email_cuenta_igual_en_mayusculas_y_con_espacios(client, ana):
    fail(client, 3, email="  Ana@TEST.com ")
    fail(client, MAX_ATTEMPTS - 3)

    assert login(client).status_code == 429


def test_cuenta_un_email_que_no_existe(client):
    fail(client, MAX_ATTEMPTS, email="nadie@test.com")

    assert login(client, email="nadie@test.com").status_code == 429


def test_cuenta_un_usuario_desactivado(client, make_user):
    make_user(Role.customer, email=EMAIL, is_active=False)
    for _ in range(MAX_ATTEMPTS):
        assert login(client).status_code == 401

    assert login(client).status_code == 429


def test_un_422_no_cuenta(client, ana):
    for _ in range(MAX_ATTEMPTS + 2):
        response = client.post("/auth/login", data={"username": EMAIL})
        assert response.status_code == 422

    assert login(client).status_code == 200


def test_avisa_en_el_log_al_bloquear_sin_la_contrasena(client, ana, caplog):
    with caplog.at_level(logging.WARNING, logger="app.services.login_rate_limit_service"):
        fail(client, MAX_ATTEMPTS)

    blocked = [r for r in caplog.records if r.getMessage() == "Login blocked"]
    assert len(blocked) == 1
    assert blocked[0].client_ip == "testclient"
    assert blocked[0].email == EMAIL
    assert "incorrecta" not in caplog.text


def test_swagger_documenta_el_429_del_login(client):
    responses = client.get("/openapi.json").json()["paths"]["/auth/login"]["post"]["responses"]

    error = responses["429"]
    assert error["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")
    assert "too_many_attempts" in error["description"]
    assert "Retry-After" in error["description"]


def enable_2fa(client):
    """Activa la 2FA de Ana y devuelve su secreto TOTP."""
    token = login(client).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    secret = client.post("/users/me/2fa/setup", headers=headers).json()["secret"]
    code = pyotp.TOTP(secret).now()
    assert client.post("/users/me/2fa/enable", headers=headers, json={"code": code}).status_code == 200
    return secret


def wrong_code(secret):
    totp = pyotp.TOTP(secret)
    now = datetime.now(UTC)
    valid = {totp.at(now + timedelta(seconds=s)) for s in (-30, 0, 30)}
    return next(c for c in (f"{n:06d}" for n in range(1000)) if c not in valid)


def verify(client, mfa_token, code):
    return client.post("/auth/2fa/verify", json={"mfa_token": mfa_token, "code": code})


def mfa_token(client):
    return login(client).json()["mfa_token"]


def fail_2fa(client, secret, times):
    for _ in range(times):
        assert verify(client, mfa_token(client), wrong_code(secret)).status_code == 401


def test_2fa_cinco_codigos_malos_dan_401_y_el_sexto_429(client, ana):
    secret = enable_2fa(client)
    fail_2fa(client, secret, MAX_ATTEMPTS)

    response = verify(client, mfa_token(client), wrong_code(secret))

    assert response.status_code == 429
    assert response.json()["code"] == "too_many_attempts"
    assert 1 <= int(response.headers["Retry-After"]) <= WINDOW_SECONDS


def test_2fa_durante_el_bloqueo_el_codigo_correcto_tambien_da_429(client, ana):
    secret = enable_2fa(client)
    fail_2fa(client, secret, MAX_ATTEMPTS)

    assert verify(client, mfa_token(client), pyotp.TOTP(secret).now()).status_code == 429


def test_2fa_un_codigo_correcto_borra_los_fallos(client, ana):
    secret = enable_2fa(client)
    fail_2fa(client, secret, MAX_ATTEMPTS - 1)
    assert verify(client, mfa_token(client), pyotp.TOTP(secret).now()).status_code == 200

    fail_2fa(client, secret, MAX_ATTEMPTS - 1)

    assert verify(client, mfa_token(client), pyotp.TOTP(secret).now()).status_code == 200


def test_2fa_cuenta_por_usuario_aunque_cambie_la_ip(client, ana, ip_header):
    secret = enable_2fa(client)
    for n in range(MAX_ATTEMPTS):
        ip = {ip_header: f"203.0.113.{n}"}
        token = login(client, headers=ip).json()["mfa_token"]
        assert client.post(
            "/auth/2fa/verify", json={"mfa_token": token, "code": wrong_code(secret)}, headers=ip
        ).status_code == 401

    other_ip = {ip_header: "198.51.100.1"}
    token = login(client, headers=other_ip).json()["mfa_token"]
    response = client.post(
        "/auth/2fa/verify",
        json={"mfa_token": token, "code": pyotp.TOTP(secret).now()},
        headers=other_ip,
    )
    assert response.status_code == 429


def test_2fa_el_bloqueo_no_afecta_a_otro_usuario(client, ana, make_user):
    secret = enable_2fa(client)
    fail_2fa(client, secret, MAX_ATTEMPTS)
    make_user(Role.waiter, email="otra@test.com")

    assert login(client, email="otra@test.com").status_code == 200


def test_2fa_un_mfa_token_no_valido_no_cuenta(client, ana):
    secret = enable_2fa(client)
    for _ in range(MAX_ATTEMPTS + 1):
        assert verify(client, "no-es-un-token", "123456").status_code == 401

    assert verify(client, mfa_token(client), pyotp.TOTP(secret).now()).status_code == 200


def test_2fa_avisa_en_el_log_al_bloquear(client, ana, caplog):
    secret = enable_2fa(client)
    with caplog.at_level(logging.WARNING, logger="app.services.login_rate_limit_service"):
        fail_2fa(client, secret, MAX_ATTEMPTS)

    blocked = [r for r in caplog.records if r.getMessage() == "Two-factor blocked"]
    assert len(blocked) == 1
    assert blocked[0].user_id == ana.id


def test_swagger_documenta_el_429_de_2fa_verify(client):
    paths = client.get("/openapi.json").json()["paths"]
    error = paths["/auth/2fa/verify"]["post"]["responses"]["429"]

    assert error["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")
    assert "too_many_attempts" in error["description"]
