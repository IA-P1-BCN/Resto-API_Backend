"""Rutas HTTP de reservas (HU-10).

Permisos (§5.4): admin y waiter operan sobre todas las reservas; customer solo
sobre las suyas (403 si intenta tocar una ajena); kitchen no tiene acceso.
La lógica de aforo y solapamiento está en app/services/reservations.py.
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ErrorResponse, ForbiddenError
from app.core.pagination import Page, PageParams, page_params, paginate
from app.core.permissions import (
    RESERVATIONS,
    CurrentUser,
    ensure_owner_or_role,
    require_role,
)
from app.models.model_user import Role, User
from app.models.reservation import Reservation
from app.schemas.reservation import (
    ReservationCreate,
    ReservationRead,
    ReservationStatus,
    ReservationUpdate,
)
from app.services import reservations as service
from app.services.notifications import send_email

router = APIRouter(
    prefix="/reservations",
    tags=["reservations"],
    dependencies=[Depends(require_role(*RESERVATIONS))],
    responses={
        401: {"description": "Falta el token o no es válido."},
        403: {
            "description": "El rol no tiene permiso o la reserva es de otro usuario."
        },
    },
)

DbSession = Annotated[Session, Depends(get_db)]
STAFF = (Role.admin, Role.waiter)


def _is_staff(user: User) -> bool:
    return user.role in {role.value for role in STAFF}


def _forbidden(detail: str) -> ForbiddenError:
    return ForbiddenError(detail, code="reservation_forbidden")


def _get_visible_reservation(
    db: Session, reservation_id: int, user: User
) -> Reservation:
    """Reserva por id (404) si el usuario es staff o su dueño (403 si no)."""
    reservation = service.get_reservation(db, reservation_id)
    ensure_owner_or_role(user, reservation.user_id, *STAFF)
    return reservation


def _errors(*codes: int) -> dict[int | str, dict[str, Any]]:
    descriptions = {
        404: "La reserva, la mesa o el usuario no existen.",
        409: "Conflicto: solapamiento con otra reserva o estado no válido.",
        422: "Datos no válidos o party_size mayor que la capacidad de la mesa.",
    }
    return {
        code: {"model": ErrorResponse, "description": descriptions[code]}
        for code in codes
    }


@router.post(
    "",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una reserva",
    description=(
        "Crea una reserva confirmada. Valida que la mesa exista (404), que "
        "`party_size` no supere su capacidad (422) y que no se solape con otra "
        "reserva activa de la misma mesa (409). Un customer solo puede reservar "
        "para sí mismo; admin y waiter pueden indicar `user_id`. "
        "Roles: admin, waiter, customer."
    ),
    responses=_errors(404, 409, 422),
)
def create_reservation(
    data: ReservationCreate, db: DbSession, user: CurrentUser
) -> Reservation:
    owner_id = data.user_id or user.id
    if owner_id != user.id:
        if not _is_staff(user):
            raise _forbidden("Solo puedes crear reservas a tu nombre")
        service.ensure_user_exists(db, owner_id)
    return service.create_reservation(db, data, owner_id)


@router.get(
    "",
    response_model=Page[ReservationRead],
    summary="Listar reservas",
    description=(
        "Lista paginada ordenada por fecha. Filtros opcionales: `status`, "
        "`table_id`, `date` (día de `reserved_at`, AAAA-MM-DD) y `user_id`. "
        "Un customer solo ve sus reservas (403 si filtra por otro `user_id`). "
        "Roles: admin, waiter, customer."
    ),
)
def list_reservations(
    db: DbSession,
    user: CurrentUser,
    params: Annotated[PageParams, Depends(page_params)],
    status_: Annotated[
        ReservationStatus | None, Query(alias="status", description="Estado.")
    ] = None,
    table_id: Annotated[int | None, Query(gt=0, description="Mesa.")] = None,
    day: Annotated[
        date | None, Query(alias="date", description="Día de la reserva (AAAA-MM-DD).")
    ] = None,
    user_id: Annotated[int | None, Query(gt=0, description="Cliente.")] = None,
) -> Page[ReservationRead]:
    if not _is_staff(user):
        if user_id is not None and user_id != user.id:
            raise _forbidden("Solo puedes ver tus propias reservas")
        user_id = user.id
    stmt = service.list_reservations_query(
        status=status_, table_id=table_id, day=day, user_id=user_id
    )
    return paginate(db, stmt, params, ReservationRead)


@router.get(
    "/{reservation_id}",
    response_model=ReservationRead,
    summary="Ver una reserva",
    description="Detalle de una reserva. Roles: admin, waiter y el dueño de la reserva.",
    responses=_errors(404),
)
def get_reservation(
    reservation_id: int, db: DbSession, user: CurrentUser
) -> Reservation:
    return _get_visible_reservation(db, reservation_id, user)


@router.patch(
    "/{reservation_id}",
    response_model=ReservationRead,
    summary="Editar una reserva",
    description=(
        "Edición parcial: solo cambian los campos enviados. Si cambia la mesa, la "
        "hora, la duración o las personas se revalidan capacidad (422) y "
        "solapamiento (409). `status` solo lo pueden cambiar admin y waiter. "
        "Roles: admin, waiter y el dueño de la reserva."
    ),
    responses=_errors(404, 409, 422),
)
def update_reservation(
    reservation_id: int, data: ReservationUpdate, db: DbSession, user: CurrentUser
) -> Reservation:
    reservation = _get_visible_reservation(db, reservation_id, user)
    if "status" in data.model_fields_set and not _is_staff(user):
        raise _forbidden("Solo admin y waiter pueden cambiar el estado de una reserva")
    return service.update_reservation(db, reservation, data)


@router.patch(
    "/{reservation_id}/cancel",
    response_model=ReservationRead,
    summary="Cancelar una reserva",
    description=(
        "Pasa la reserva a `cancelled` y libera el hueco de la mesa. Envía un email "
        "de cancelación en segundo plano (si `EMAIL_ENABLED=false` solo se registra "
        "en el log). 409 si la reserva no está confirmada. "
        "Roles: admin, waiter y el dueño de la reserva."
    ),
    responses=_errors(404, 409),
)
def cancel_reservation(
    reservation_id: int,
    db: DbSession,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> Reservation:
    reservation = _get_visible_reservation(db, reservation_id, user)
    reservation = service.cancel_reservation(db, reservation)
    email = service.cancellation_email(db, reservation)
    if email is not None:
        background_tasks.add_task(send_email, *email)
    return reservation


@router.delete(
    "/{reservation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Borrar una reserva",
    description=(
        "Borra la reserva definitivamente. Para conservar el historial es "
        "preferible cancelarla. Roles: admin, waiter y el dueño de la reserva."
    ),
    responses=_errors(404),
)
def delete_reservation(reservation_id: int, db: DbSession, user: CurrentUser) -> None:
    reservation = _get_visible_reservation(db, reservation_id, user)
    service.delete_reservation(db, reservation)
