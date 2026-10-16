"""Límite de intentos de login (HU-31, R-10).

Los fallos se cuentan en memoria en una ventana fija: empieza en el primer fallo y dura
`LOGIN_WINDOW_MINUTES`. Al llegar a `LOGIN_MAX_ATTEMPTS` fallos, la clave queda bloqueada
hasta que acaba la ventana, y un acierto borra el contador. Hay dos límites:

- `login_rate_limiter`: contraseña de `POST /auth/login`, por pareja `(client_ip, email)`.
- `two_factor_rate_limiter`: código de `POST /auth/2fa/verify`, por usuario (HU-37).
"""

import logging
import math
import threading
import time
from collections.abc import Callable, Hashable
from dataclasses import dataclass

from cachetools import TTLCache

from app.config import settings
from app.core.exceptions import TooManyRequestsError
from app.services.user_service import normalize_email

logger = logging.getLogger(__name__)

TOO_MANY_ATTEMPTS_CODE = "too_many_attempts"
TOO_MANY_ATTEMPTS_DETAIL = "Too many failed login attempts. Try again later."
MAX_TRACKED_KEYS = 10_000

Timer = Callable[[], float]


@dataclass
class _Attempts:
    count: int
    first_failure: float


class FixedWindowCounter:
    """Fallos por clave en una ventana fija que empieza en el primer fallo."""

    def __init__(self, max_attempts: int, window_seconds: int, timer: Timer = time.monotonic) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._timer = timer
        self._attempts: TTLCache[Hashable, _Attempts] = TTLCache(
            maxsize=MAX_TRACKED_KEYS, ttl=window_seconds, timer=timer
        )
        self._lock = threading.Lock()

    def retry_after(self, key: Hashable) -> int | None:
        """Segundos que faltan para que acabe el bloqueo, o `None` si no está bloqueada."""
        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None or attempts.count < self.max_attempts:
                return None
            remaining = self.window_seconds - (self._timer() - attempts.first_failure)
        return max(1, math.ceil(remaining))

    def check(self, key: Hashable) -> None:
        """Lanza `TooManyRequestsError` (429) si la clave está bloqueada."""
        retry_after = self.retry_after(key)
        if retry_after is not None:
            raise TooManyRequestsError(
                TOO_MANY_ATTEMPTS_DETAIL, retry_after=retry_after, code=TOO_MANY_ATTEMPTS_CODE
            )

    def register_failure(self, key: Hashable) -> bool:
        """Suma un fallo sin alargar la ventana. Devuelve `True` si este fallo bloquea."""
        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None:
                attempts = _Attempts(count=0, first_failure=self._timer())
                self._attempts[key] = attempts
            attempts.count += 1
            return attempts.count == self.max_attempts

    def reset(self, key: Hashable) -> None:
        """Borra los fallos de la clave tras un acierto."""
        with self._lock:
            self._attempts.pop(key, None)

    def clear(self) -> None:
        """Borra todos los contadores (lo usan los tests)."""
        with self._lock:
            self._attempts.clear()


class LoginRateLimiter:
    """Límite de la contraseña: cuenta los fallos por `(client_ip, email)`."""

    def __init__(self, max_attempts: int, window_seconds: int, timer: Timer = time.monotonic) -> None:
        self._counter = FixedWindowCounter(max_attempts, window_seconds, timer)

    def check(self, client_ip: str, email: str) -> None:
        self._counter.check(_login_key(client_ip, email))

    def retry_after(self, client_ip: str, email: str) -> int | None:
        return self._counter.retry_after(_login_key(client_ip, email))

    def register_failure(self, client_ip: str, email: str) -> None:
        key = _login_key(client_ip, email)
        if self._counter.register_failure(key):
            logger.warning("Login blocked", extra={"client_ip": key[0], "email": key[1]})

    def reset(self, client_ip: str, email: str) -> None:
        self._counter.reset(_login_key(client_ip, email))

    def clear(self) -> None:
        self._counter.clear()


class TwoFactorRateLimiter:
    """Límite del código 2FA: cuenta los fallos por usuario.

    Va por usuario y no por IP porque para llegar al código hay que saber la contraseña:
    nadie sin ella puede bloquear a otro, y quien la sabe no puede cambiar de IP para seguir
    probando códigos.
    """

    def __init__(self, max_attempts: int, window_seconds: int, timer: Timer = time.monotonic) -> None:
        self._counter = FixedWindowCounter(max_attempts, window_seconds, timer)

    def check(self, user_id: int) -> None:
        self._counter.check(user_id)

    def retry_after(self, user_id: int) -> int | None:
        return self._counter.retry_after(user_id)

    def register_failure(self, user_id: int) -> None:
        if self._counter.register_failure(user_id):
            logger.warning("Two-factor blocked", extra={"user_id": user_id})

    def reset(self, user_id: int) -> None:
        self._counter.reset(user_id)

    def clear(self) -> None:
        self._counter.clear()


def _login_key(client_ip: str, email: str) -> tuple[str, str]:
    return client_ip, normalize_email(email)


login_rate_limiter = LoginRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_WINDOW_MINUTES * 60,
)

two_factor_rate_limiter = TwoFactorRateLimiter(
    max_attempts=settings.LOGIN_MAX_ATTEMPTS,
    window_seconds=settings.LOGIN_WINDOW_MINUTES * 60,
)
