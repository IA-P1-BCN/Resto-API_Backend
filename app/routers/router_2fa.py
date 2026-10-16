"""Verificación en dos pasos con TOTP (HU-37): segundo paso del login y gestión desde el perfil."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.openapi import error_responses
from app.core.permissions import CurrentUser
from app.core.security import create_access_token
from app.database import get_db
from app.schemas.schema_2fa import (
    RecoveryCodesOut,
    TwoFactorCodeRequest,
    TwoFactorSetupOut,
    TwoFactorStatusOut,
    TwoFactorVerifyRequest,
)
from app.schemas.schema_auth import TokenOut
from app.services import totp_service

router = APIRouter(prefix="/auth/2fa", tags=["auth"])
me_router = APIRouter(prefix="/users/me/2fa", tags=["users"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/verify",
    response_model=TokenOut,
    summary="Segundo paso del login con verificación en dos pasos",
    responses=error_responses(
        401,
        422,
        429,
        descriptions={
            401: "Token temporal no válido o caducado, o cuenta desactivada (`invalid_mfa_token`), "
            "o código incorrecto (`invalid_totp_code`).",
            422: "Datos no válidos (`validation_error`).",
            429: "Demasiados códigos incorrectos para esta cuenta (`too_many_attempts`, R-10, "
            "HU-31). La cabecera `Retry-After` indica cuántos segundos faltan.",
        },
    ),
)
def verify(data: TwoFactorVerifyRequest, db: DbSession) -> dict:
    """Canjea el `mfa_token` del login y un código (TOTP o de recuperación) por el JWT.

    Si la cuenta tiene la verificación en dos pasos, `POST /auth/login` y
    `POST /auth/social/{provider}` responden `{"mfa_required": true, "mfa_token": "..."}`
    en lugar del token. El `mfa_token` caduca en 5 minutos y un código de recuperación
    solo sirve una vez. Tras `LOGIN_MAX_ATTEMPTS` códigos incorrectos (5) en
    `LOGIN_WINDOW_MINUTES` (15), la cuenta recibe `429` hasta que acaba la ventana, también
    con un código correcto (HU-31). Rol: público.
    """
    user = totp_service.verify_challenge(db, data.mfa_token, data.code)
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@me_router.get(
    "",
    response_model=TwoFactorStatusOut,
    summary="Estado de mi verificación en dos pasos",
    responses=error_responses(401),
)
def get_status(current_user: CurrentUser) -> dict:
    """Si está activada y cuántos códigos de recuperación quedan. Rol: cualquiera autenticado."""
    enabled, left = totp_service.status_of(current_user)
    return {"enabled": enabled, "recovery_codes_left": left}


@me_router.post(
    "/setup",
    response_model=TwoFactorSetupOut,
    summary="Preparar la verificación en dos pasos",
    responses=error_responses(401, 409, descriptions={409: "Ya está activada (`totp_already_enabled`)."}),
)
def setup(db: DbSession, current_user: CurrentUser) -> dict:
    """Genera un secreto nuevo, aún sin activar, con su QR. Rol: cualquiera autenticado."""
    secret, uri, qr_svg = totp_service.setup(db, current_user)
    return {"secret": secret, "otpauth_uri": uri, "qr_svg": qr_svg}


@me_router.post(
    "/enable",
    response_model=RecoveryCodesOut,
    summary="Activar la verificación en dos pasos",
    responses=error_responses(
        400,
        401,
        409,
        422,
        descriptions={
            400: "Código incorrecto (`invalid_totp_code`).",
            409: "Ya está activada (`totp_already_enabled`) o falta `setup` (`totp_not_set_up`).",
        },
    ),
)
def enable(data: TwoFactorCodeRequest, db: DbSession, current_user: CurrentUser) -> dict:
    """Activa la 2FA con un primer código de la app y devuelve 8 códigos de recuperación.

    Los códigos solo se muestran esta vez. Rol: cualquiera autenticado.
    """
    return {"recovery_codes": totp_service.enable(db, current_user, data.code)}


@me_router.post(
    "/disable",
    response_model=TwoFactorStatusOut,
    summary="Desactivar la verificación en dos pasos",
    responses=error_responses(
        400,
        401,
        409,
        422,
        descriptions={
            400: "Código incorrecto (`invalid_totp_code`).",
            409: "No está activada (`totp_not_enabled`).",
        },
    ),
)
def disable(data: TwoFactorCodeRequest, db: DbSession, current_user: CurrentUser) -> dict:
    """Desactiva la 2FA con un código de la app o de recuperación. Rol: cualquiera autenticado."""
    totp_service.disable(db, current_user, data.code)
    return {"enabled": False, "recovery_codes_left": 0}
