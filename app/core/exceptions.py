"""API errors with the common format {"detail": str, "code": str} (R-04 / HU-11).
 
- Business errors: raise NotFoundError, ConflictError, ForbiddenError or
  UnprocessableError from services/crud. Each class sets its status code.
- Global handlers (registered in main.py with register_exception_handlers):
  * AppError and any HTTPException  -> its status, {"detail", "code"}
  * Request validation errors (422) -> {"detail", "code", "errors": [...]}
  * Any unexpected exception (500)  -> generic message; full traceback in logs
"""
 
import logging
 
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
 
logger = logging.getLogger(__name__)
 
BAD_REQUEST_CODE = "bad_request"
UNAUTHORIZED_CODE = "unauthorized"
FORBIDDEN_CODE = "forbidden"
NOT_FOUND_CODE = "not_found"
METHOD_NOT_ALLOWED_CODE = "method_not_allowed"
CONFLICT_CODE = "conflict"
UNPROCESSABLE_CODE = "unprocessable"
VALIDATION_ERROR_CODE = "validation_error"
INTERNAL_ERROR_CODE = "internal_error"
HTTP_ERROR_CODE = "http_error"
 
CODES_BY_STATUS = {
    status.HTTP_400_BAD_REQUEST: BAD_REQUEST_CODE,
    status.HTTP_401_UNAUTHORIZED: UNAUTHORIZED_CODE,
    status.HTTP_403_FORBIDDEN: FORBIDDEN_CODE,
    status.HTTP_404_NOT_FOUND: NOT_FOUND_CODE,
    status.HTTP_405_METHOD_NOT_ALLOWED: METHOD_NOT_ALLOWED_CODE,
    status.HTTP_409_CONFLICT: CONFLICT_CODE,
    status.HTTP_422_UNPROCESSABLE_CONTENT: UNPROCESSABLE_CODE,
}
 
VALIDATION_ERROR_DETAIL = "Invalid request data"
INTERNAL_ERROR_DETAIL = "Internal server error"
 
 
class AppError(HTTPException):
    """Business error with a code the frontend can read."""
 
    status_code: int = status.HTTP_400_BAD_REQUEST
    default_code: str = BAD_REQUEST_CODE
 
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
    """Well-formed data that breaks a business rule (422)."""
 
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    default_code = UNPROCESSABLE_CODE
 
 
class ReservationConflict(ConflictError):
    """The reservation overlaps another active reservation of the same table."""
 
    default_code = "reservation_conflict"
 
 
def _error_body(detail: object, code: str) -> dict:
    return {"detail": detail if isinstance(detail, str) else str(detail), "code": code}
 
 
def _request_info(request: Request) -> dict:
    return {"method": request.method, "path": request.url.path}
 
 
async def http_error_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """AppError and any HTTPException: same status, body {"detail", "code"}."""
    code = getattr(exc, "code", None) or CODES_BY_STATUS.get(
        exc.status_code, HTTP_ERROR_CODE
    )
    logger.warning(
        "HTTP error",
        extra={"status_code": exc.status_code, "code": code, **_request_info(request)},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.detail, code),
        headers=getattr(exc, "headers", None),
    )
 
 
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """422 from FastAPI/Pydantic: generic detail plus the list of field errors."""
    errors = jsonable_encoder(exc.errors(), exclude={"input", "ctx", "url"})
    logger.warning(
        "Validation error",
        extra={
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "code": VALIDATION_ERROR_CODE,
            "fields": [".".join(str(p) for p in e.get("loc", ())) for e in errors],
            **_request_info(request),
        },
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            **_error_body(VALIDATION_ERROR_DETAIL, VALIDATION_ERROR_CODE),
            "errors": errors,
        },
    )
 
 
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """500: the client gets a generic message; the traceback goes to the logs."""
    logger.exception("Unhandled error", extra=_request_info(request))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(INTERNAL_ERROR_DETAIL, INTERNAL_ERROR_CODE),
    )
 
 
app_error_handler = http_error_handler
 
 
def register_exception_handlers(app: FastAPI) -> None:
    """Connect the global handlers to the app. Call it once in main.py."""
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
 
 
class ErrorResponse(BaseModel):
    """API error format (to document responses in Swagger)."""
 
    detail: str = Field(examples=["Dish 42 not found"])
    code: str = Field(examples=[NOT_FOUND_CODE])

