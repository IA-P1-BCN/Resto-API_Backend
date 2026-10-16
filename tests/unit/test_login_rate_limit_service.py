"""HU-31 / R-10: límite de intentos de login (service, con reloj falso)."""

import logging

import pytest

from app.core.exceptions import CODES_BY_STATUS, TooManyRequestsError
from app.core.openapi import error_responses
from app.services.login_rate_limit_service import (
    TOO_MANY_ATTEMPTS_CODE,
    TOO_MANY_ATTEMPTS_DETAIL,
    LoginRateLimiter,
    TwoFactorRateLimiter,
)

IP = "203.0.113.7"
EMAIL = "ana@example.com"
WINDOW = 900


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def limiter(clock) -> LoginRateLimiter:
    return LoginRateLimiter(max_attempts=5, window_seconds=WINDOW, timer=clock)


def fail(limiter: LoginRateLimiter, times: int, ip: str = IP, email: str = EMAIL) -> None:
    for _ in range(times):
        limiter.register_failure(ip, email)


def test_cuatro_fallos_no_bloquean(limiter):
    fail(limiter, 4)

    assert limiter.retry_after(IP, EMAIL) is None
    limiter.check(IP, EMAIL)


def test_el_quinto_fallo_bloquea_con_429_y_retry_after(limiter):
    fail(limiter, 5)

    with pytest.raises(TooManyRequestsError) as exc_info:
        limiter.check(IP, EMAIL)

    error = exc_info.value
    assert error.status_code == 429
    assert error.code == TOO_MANY_ATTEMPTS_CODE
    assert error.detail == TOO_MANY_ATTEMPTS_DETAIL
    assert error.headers == {"Retry-After": str(WINDOW)}


def test_retry_after_baja_con_el_tiempo_y_redondea_hacia_arriba(limiter, clock):
    fail(limiter, 5)

    clock.advance(100.4)

    assert limiter.retry_after(IP, EMAIL) == WINDOW - 100


def test_la_ventana_empieza_en_el_primer_fallo_y_no_se_alarga(limiter, clock):
    limiter.register_failure(IP, EMAIL)
    clock.advance(600)
    fail(limiter, 4)

    assert limiter.retry_after(IP, EMAIL) == WINDOW - 600

    clock.advance(WINDOW - 600)

    assert limiter.retry_after(IP, EMAIL) is None
    limiter.check(IP, EMAIL)


def test_los_fallos_caducan_al_acabar_la_ventana(limiter, clock):
    fail(limiter, 4)
    clock.advance(WINDOW)
    limiter.register_failure(IP, EMAIL)

    assert limiter.retry_after(IP, EMAIL) is None


def test_reset_borra_el_contador(limiter):
    fail(limiter, 4)
    limiter.reset(IP, EMAIL)
    fail(limiter, 4)

    assert limiter.retry_after(IP, EMAIL) is None


def test_reset_sin_contador_no_falla(limiter):
    limiter.reset(IP, EMAIL)


def test_cuenta_por_pareja_ip_y_email(limiter):
    fail(limiter, 5)

    assert limiter.retry_after("198.51.100.1", EMAIL) is None
    assert limiter.retry_after(IP, "otra@example.com") is None


def test_el_email_se_normaliza(limiter):
    fail(limiter, 3, email="  Ana@Example.COM ")
    fail(limiter, 2, email=EMAIL)

    assert limiter.retry_after(IP, EMAIL) == WINDOW


def test_clear_borra_todos_los_contadores(limiter):
    fail(limiter, 5)
    fail(limiter, 5, ip="198.51.100.1")

    limiter.clear()

    assert limiter.retry_after(IP, EMAIL) is None
    assert limiter.retry_after("198.51.100.1", EMAIL) is None


def test_avisa_en_el_log_una_sola_vez_al_bloquear(limiter, caplog):
    with caplog.at_level(logging.WARNING, logger="app.services.login_rate_limit_service"):
        fail(limiter, 7, email="Ana@Example.com")

    blocked = [r for r in caplog.records if r.getMessage() == "Login blocked"]
    assert len(blocked) == 1
    assert blocked[0].client_ip == IP
    assert blocked[0].email == EMAIL
    assert not hasattr(blocked[0], "password")


def test_el_429_tiene_codigo_y_descripcion_por_defecto():
    assert CODES_BY_STATUS[429] == "too_many_requests"
    assert "Retry-After" in error_responses(429)[429]["description"]


def test_2fa_bloquea_por_usuario_y_se_resetea(clock):
    limiter = TwoFactorRateLimiter(max_attempts=5, window_seconds=WINDOW, timer=clock)
    for _ in range(5):
        limiter.register_failure(7)

    with pytest.raises(TooManyRequestsError):
        limiter.check(7)
    assert limiter.retry_after(8) is None

    limiter.reset(7)
    limiter.check(7)


def test_2fa_clear_y_caducidad(clock):
    limiter = TwoFactorRateLimiter(max_attempts=5, window_seconds=WINDOW, timer=clock)
    for _ in range(5):
        limiter.register_failure(7)
    clock.advance(WINDOW)

    assert limiter.retry_after(7) is None

    for _ in range(5):
        limiter.register_failure(7)
    limiter.clear()
    assert limiter.retry_after(7) is None
