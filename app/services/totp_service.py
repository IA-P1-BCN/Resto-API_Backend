"""Verificación en dos pasos con TOTP (HU-37, R-12).

El secreto se guarda cifrado con Fernet y los códigos de recuperación solo con su
SHA-256. Ni el secreto ni los códigos se registran nunca en el log. El token temporal
del login lleva `aud: "2fa"`, así que la validación del access token lo rechaza.
"""

import base64
import hashlib
import io
import logging
import secrets
from datetime import UTC, datetime, timedelta

import jwt
import pyotp
import segno
from cryptography.fernet import Fernet, InvalidToken
from fastapi import status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import AppError, ConflictError, UnauthorizedError
from app.models.model_user import User
from app.repositories import user_repository
from app.schemas.schema_2fa import TwoFactorChallengeOut
from app.services.login_rate_limit_service import two_factor_rate_limiter

logger = logging.getLogger(__name__)

ISSUER = "APIResto"
MFA_AUDIENCE = "2fa"
MFA_TOKEN_MINUTES = 5
RECOVERY_CODES = 8
VALID_WINDOW = 1


class InvalidCodeError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "invalid_totp_code"


def _fernet() -> Fernet:
    key = settings.TOTP_ENCRYPTION_KEY or base64.urlsafe_b64encode(
        hashlib.sha256(settings.JWT_SECRET_KEY.encode("utf-8")).digest()
    ).decode("ascii")
    return Fernet(key)


def _encrypt(secret: str) -> str:
    return _fernet().encrypt(secret.encode("utf-8")).decode("ascii")


def _decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return None


def _normalize(code: str) -> str:
    return code.replace(" ", "").replace("-", "").lower()


def _hash_code(code: str) -> str:
    return hashlib.sha256(_normalize(code).encode("utf-8")).hexdigest()


def _recovery_hashes(user: User) -> list[str]:
    return [h for h in (user.totp_recovery_codes or "").split(",") if h]


def _totp_matches(user: User, code: str) -> bool:
    secret = _decrypt(user.totp_secret) if user.totp_secret else None
    normalized = _normalize(code)
    return bool(secret) and normalized.isdigit() and pyotp.TOTP(secret).verify(normalized, valid_window=VALID_WINDOW)


def _accept_code(db: Session, user: User, code: str) -> bool:
    """TOTP válido o código de recuperación sin usar (que se gasta con la fila bloqueada)."""
    if _totp_matches(user, code):
        return True
    hashed = _hash_code(code)
    if hashed not in _recovery_hashes(user):
        return False
    locked = user_repository.get_by_id_for_update(db, user.id)
    hashes = _recovery_hashes(locked) if locked else []
    if hashed not in hashes:
        db.rollback()
        return False
    hashes.remove(hashed)
    locked.totp_recovery_codes = ",".join(hashes)
    user_repository.save(db, locked)
    logger.info("Recovery code used", extra={"user_id": user.id, "left": len(hashes)})
    return True


def _qr_svg(uri: str) -> str:
    """SVG completo (con xmlns y fondo blanco) para usarlo como imagen `data:` en la web."""
    buffer = io.BytesIO()
    segno.make(uri, error="m").save(buffer, kind="svg", scale=4, light="#fff", xmldecl=False, nl=False)
    return buffer.getvalue().decode("utf-8")


def status_of(user: User) -> tuple[bool, int]:
    return bool(user.totp_enabled), len(_recovery_hashes(user)) if user.totp_enabled else 0


def setup(db: Session, user: User) -> tuple[str, str, str]:
    """Genera y guarda (cifrado) un secreto nuevo sin activar. Devuelve secreto, URI y QR."""
    if user.totp_enabled:
        raise ConflictError("Two-factor authentication is already enabled", code="totp_already_enabled")
    secret = pyotp.random_base32()
    user.totp_secret = _encrypt(secret)
    user_repository.save(db, user)
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=ISSUER)
    qr_svg = _qr_svg(uri)
    logger.info("Two-factor setup started", extra={"user_id": user.id})
    return secret, uri, qr_svg


def enable(db: Session, user: User, code: str) -> list[str]:
    """Activa la 2FA con un primer código válido y devuelve los códigos de recuperación."""
    if user.totp_enabled:
        raise ConflictError("Two-factor authentication is already enabled", code="totp_already_enabled")
    if not user.totp_secret:
        raise ConflictError("Two-factor authentication is not set up", code="totp_not_set_up")
    if not _totp_matches(user, code):
        logger.warning("Two-factor enable rejected", extra={"user_id": user.id, "code": "invalid_totp_code"})
        raise InvalidCodeError("Invalid two-factor code")
    codes = [f"{secrets.token_hex(5)}-{secrets.token_hex(5)}" for _ in range(RECOVERY_CODES)]
    user.totp_recovery_codes = ",".join(_hash_code(c) for c in codes)
    user.totp_enabled = True
    user_repository.save(db, user)
    logger.info("Two-factor enabled", extra={"user_id": user.id})
    return codes


def disable(db: Session, user: User, code: str) -> None:
    """Desactiva la 2FA con un TOTP o un código de recuperación válido."""
    if not user.totp_enabled:
        raise ConflictError("Two-factor authentication is not enabled", code="totp_not_enabled")
    if not _accept_code(db, user, code):
        logger.warning("Two-factor disable rejected", extra={"user_id": user.id, "code": "invalid_totp_code"})
        raise InvalidCodeError("Invalid two-factor code")
    user.totp_enabled = False
    user.totp_secret = None
    user.totp_recovery_codes = None
    user_repository.save(db, user)
    logger.info("Two-factor disabled", extra={"user_id": user.id})


def start_challenge(user: User) -> dict:
    """Reto del login para una cuenta con 2FA: token temporal en lugar del JWT."""
    payload = {
        "sub": str(user.id),
        "aud": MFA_AUDIENCE,
        "exp": datetime.now(UTC) + timedelta(minutes=MFA_TOKEN_MINUTES),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    logger.info("Two-factor challenge issued", extra={"user_id": user.id})
    return TwoFactorChallengeOut(mfa_token=token).model_dump()


def verify_challenge(db: Session, mfa_token: str, code: str) -> User:
    """Segundo paso del login. Devuelve el usuario si el token y el código son válidos."""
    try:
        payload = jwt.decode(
            mfa_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], audience=MFA_AUDIENCE
        )
        user = user_repository.get_by_id(db, int(payload["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError):
        user = None
    if user is None or not user.is_active or user.deleted_at is not None or not user.totp_enabled:
        logger.warning("Two-factor verify rejected", extra={"code": "invalid_mfa_token"})
        raise UnauthorizedError("Invalid or expired two-factor token", code="invalid_mfa_token")
    two_factor_rate_limiter.check(user.id)
    if not _accept_code(db, user, code):
        two_factor_rate_limiter.register_failure(user.id)
        logger.warning("Two-factor verify rejected", extra={"user_id": user.id, "code": "invalid_totp_code"})
        raise UnauthorizedError("Invalid two-factor code", code="invalid_totp_code")
    two_factor_rate_limiter.reset(user.id)
    logger.info("Two-factor verify accepted", extra={"user_id": user.id})
    return user
