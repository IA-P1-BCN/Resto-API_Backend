from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Request,
    status,
)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.core.openapi import error_responses
from app.core.permissions import CurrentUser
from app.core.security import create_access_token
from app.database import get_db
from app.schemas.schema_auth import TokenOut
from app.schemas.schema_social import SocialLoginRequest, SocialProvider
from app.schemas.schema_user import UserOut, UserRegister
from app.services import email_verification_service, social_auth_service, user_service
from app.services.auth_emails import verification_email
from app.services.login_rate_limit_service import login_rate_limiter
from app.services.notifications import send_email
from app.services.totp_service import start_challenge

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]

MAX_IP_LENGTH = 45


def client_ip(request: Request) -> str:
    """IP del cliente para el límite de login (HU-31).

    Si `CLIENT_IP_HEADER` está configurada y la cabecera llega, se usa su valor; si no, la
    IP de la conexión. Nunca se lee `X-Forwarded-For`, que lo puede escribir el cliente.
    """
    if settings.CLIENT_IP_HEADER:
        value = request.headers.get(settings.CLIENT_IP_HEADER, "").strip()
        if value:
            return value[:MAX_IP_LENGTH]
    return request.client.host if request.client else "unknown"


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Auto-registro de cliente",
    responses=error_responses(
        409,
        422,
        descriptions={
            409: "El email ya está registrado (`conflict`, R-01).",
            422: "Datos no válidos, por ejemplo una contraseña de menos de 8 caracteres "
            "(`validation_error`, R-02).",
        },
    ),
)
def register(data: UserRegister, db: DbSession, background_tasks: BackgroundTasks):
    """Crea una cuenta `customer` activa al instante (R-03).

    No emite token: el usuario inicia sesión después con `POST /auth/login`. El `role`
    del payload se ignora. La cuenta nace con `email_verified=false` y se le envía en
    segundo plano un email con un enlace de verificación (R-15, decisión D). La
    verificación es informativa: no impide iniciar sesión (decisión A). Rol: público.
    """
    user, token = email_verification_service.register_user(db, data)
    background_tasks.add_task(send_email, *verification_email(user, token))
    return user


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Iniciar sesión",
    responses=error_responses(
        401,
        422,
        429,
        descriptions={
            401: "Credenciales incorrectas, usuario desactivado o borrado, o cuenta sin "
            "contraseña porque solo entra con Google o GitHub (`unauthorized`).",
            422: "Falta `username` o `password` (`validation_error`).",
            429: "Demasiados intentos fallidos desde esta IP para este email "
            "(`too_many_attempts`, R-10). La cabecera `Retry-After` indica cuántos "
            "segundos faltan para poder volver a intentarlo.",
        },
    ),
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
    request: Request,
):
    """Inicia sesión con email y contraseña y devuelve un token JWT.

    Es un formulario `application/x-www-form-urlencoded` (estándar OAuth2): `username` es
    el email. En Swagger basta con pulsar **Authorize**, que usa este endpoint. Desde otra
    aplicación, envía el `access_token` en la cabecera `Authorization: Bearer <token>`.

    Límite de intentos (R-10): tras `LOGIN_MAX_ATTEMPTS` fallos (5) desde la misma IP para
    el mismo email en `LOGIN_WINDOW_MINUTES` (15) desde el primero, responde `429` hasta que
    acaba la ventana, también con la contraseña correcta. Un login correcto borra los
    fallos. Rol: público.
    """
    ip = client_ip(request)
    login_rate_limiter.check(ip, form_data.username)

    user = user_service.authenticate(db, form_data.username, form_data.password)
    if user is None:
        login_rate_limiter.register_failure(ip, form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    login_rate_limiter.reset(ip, form_data.username)
    if user.totp_enabled:
        return JSONResponse(start_challenge(user))
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.post(
    "/social/{provider}",
    response_model=TokenOut,
    summary="Login con Google o GitHub",
    responses=error_responses(
        401,
        422,
        502,
        503,
        descriptions={
            401: "`code` inválido o caducado (`invalid_code`), el proveedor no da un email "
            "verificado (`email_not_verified`) o la cuenta está desactivada o borrada "
            "(`inactive_account`).",
            422: "`redirect_uri` fuera de los orígenes permitidos "
            "(`redirect_uri_not_allowed`) o datos no válidos, incluido un `provider` "
            "desconocido (`validation_error`).",
            502: "Google o GitHub no responden (`provider_unavailable`).",
            503: "Falta el client id o el secreto del proveedor "
            "(`provider_not_configured`).",
        },
    ),
)
def social_login(
    provider: Annotated[
        SocialProvider,
        Path(description="Proveedor OAuth: `google` o `github`.", examples=["google"]),
    ],
    data: SocialLoginRequest,
    db: DbSession,
):
    """Intercambia el `code` OAuth del proveedor y devuelve un token JWT (HU-38).

    Crea un `customer` si no existe, o vincula la cuenta si el email está verificado.
    Rol: público.
    """
    user = social_auth_service.login(db, provider, data)
    if user.totp_enabled:
        return JSONResponse(start_challenge(user))
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserOut,
    summary="Datos del usuario autenticado",
    responses=error_responses(401),
)
def get_me(current_user: CurrentUser):
    """Devuelve los datos del usuario autenticado. Rol: cualquier usuario autenticado."""
    return current_user
