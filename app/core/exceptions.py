"""Excepciones de la API con el formato de error {"detail": str, "code": str} (§5.2).

Heredan de HTTPException: aunque no se registre el handler, FastAPI responde con
el status correcto. Con el handler (register_exception_handlers) el cuerpo
incluye además el campo "code".
TODO(Rita, R-04 / HU-11): completar con logging estructurado y el resto de errores.
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

NOT_FOUND_CODE = "not_found"
CONFLICT_CODE = "conflict"
FORBIDDEN_CODE = "forbidden"
UNPROCESSABLE_CODE = "unprocessable"


class AppError(HTTPException):
    """Error de negocio con un código legible por el frontend."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    default_code: str = "bad_request"

    def __init__(self, detail: str, *, code: str | None = None) -> None:
        super().__init__(status_code=self.status_code, detail=detail)
        self.code = code or self.default_code


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = NOT_FOUND_CODE


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    default_code = CONFLICT_CODE


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = FORBIDDEN_CODE


class UnprocessableError(AppError):
    """Datos bien formados pero que incumplen una regla de negocio (422)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    default_code = UNPROCESSABLE_CODE


class ReservationConflict(ConflictError):
    """La reserva se solapa con otra reserva activa de la misma mesa."""

    default_code = "reservation_conflict"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
        headers=exc.headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)


class ErrorResponse(BaseModel):
    """Formato de error de la API (para documentar las respuestas en Swagger)."""

    detail: str = Field(examples=["La reserva 42 no existe"])
    code: str = Field(examples=[NOT_FOUND_CODE])
