"""Piezas comunes para documentar la API en Swagger (HU-26).

- `ValidationErrorResponse`: cuerpo real del 422, con `errors` por campo.
- `error_responses(...)`: el dict `responses=` de FastAPI para los errores de un endpoint.
- `API_DESCRIPTION` y `OPENAPI_TAGS`: texto general de `/docs`, conectado en `main.py`.
"""

from collections.abc import Mapping
from typing import Any

from fastapi import status
from pydantic import Field

from app.core.exceptions import (
    VALIDATION_ERROR_CODE,
    VALIDATION_ERROR_DETAIL,
    ErrorResponse,
)

DEFAULT_DESCRIPTIONS: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "Petición incorrecta.",
    status.HTTP_401_UNAUTHORIZED: "Falta el token o no es válido.",
    status.HTTP_403_FORBIDDEN: "El rol del usuario no permite esta operación.",
    status.HTTP_404_NOT_FOUND: "El recurso no existe.",
    status.HTTP_409_CONFLICT: "La petición choca con el estado actual de los datos.",
    status.HTTP_422_UNPROCESSABLE_CONTENT: (
        f"Datos no válidos (`{VALIDATION_ERROR_CODE}`)."
    ),
    status.HTTP_429_TOO_MANY_REQUESTS: (
        "Demasiados intentos; la cabecera `Retry-After` indica cuántos segundos esperar."
    ),
    status.HTTP_502_BAD_GATEWAY: "Un proveedor externo no responde.",
    status.HTTP_503_SERVICE_UNAVAILABLE: "La función no está configurada en el servidor.",
}


class ValidationErrorResponse(ErrorResponse):
    """Cuerpo del 422: el formato común más, en los de validación, el detalle por campo."""

    detail: str = Field(examples=[VALIDATION_ERROR_DETAIL])
    code: str = Field(examples=[VALIDATION_ERROR_CODE])
    errors: list[dict[str, Any]] | None = Field(
        default=None,
        description=(
            f"Solo con `code` = `{VALIDATION_ERROR_CODE}`: un elemento por campo no válido. "
            "Los 422 de reglas de negocio (por ejemplo `same_password`) no lo incluyen."
        ),
        examples=[
            [{"type": "missing", "loc": ["body", "email"], "msg": "Field required"}]
        ],
    )


def error_responses(
    *statuses: int, descriptions: Mapping[int, str] | None = None
) -> dict[int | str, dict[str, Any]]:
    """Devuelve el `responses=` de un endpoint para los códigos de error indicados.

    El 422 usa `ValidationErrorResponse`; el resto, `ErrorResponse`. `descriptions`
    sustituye el texto por defecto de un código cuando el endpoint tiene algo concreto
    que decir (por ejemplo, qué `code` devuelve).
    """
    custom = descriptions or {}
    responses: dict[int | str, dict[str, Any]] = {}
    for code in statuses:
        description = custom.get(code) or DEFAULT_DESCRIPTIONS.get(code)
        if description is None:
            raise ValueError(f"Falta la descripción del error {code}")
        model = (
            ValidationErrorResponse
            if code == status.HTTP_422_UNPROCESSABLE_CONTENT
            else ErrorResponse
        )
        responses[code] = {"model": model, "description": description}
    return responses


API_DESCRIPTION = """\
API REST de gestión de un restaurante: carta, mesas, reservas, pedidos, facturas y usuarios.

## Cómo autenticarse
1. Crea una cuenta con `POST /auth/register`, o usa la que te haya dado un admin.
2. Pulsa **Authorize**, escribe tu email en `username` y tu contraseña en `password`, y deja
   vacíos `client_id` y `client_secret`. Swagger añade el token a todas las peticiones.
3. Desde otra aplicación, llama a `POST /auth/login` y envía el `access_token` recibido en la
   cabecera `Authorization: Bearer <token>`.

## Errores
Todos los errores devuelven `{"detail": "...", "code": "..."}`. El 422 de validación añade
`errors`, con el detalle de cada campo no válido.

## Roles
`admin`, `waiter`, `kitchen`, `bartender` y `customer`. Los endpoints de `auth` y `users`
indican qué rol puede llamarlos.
"""

OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "auth",
        "description": (
            "Registro, inicio de sesión (contraseña, Google o GitHub) y datos del usuario "
            "autenticado. Son públicos salvo `GET /auth/me`."
        ),
    },
    {
        "name": "users",
        "description": (
            "Gestión de usuarios. Solo `admin` puede crear, listar, editar, desactivar, "
            "borrar y restaurar. Cualquier usuario autenticado puede editar su perfil y "
            "cambiar su contraseña en `/users/me`."
        ),
    },
]
