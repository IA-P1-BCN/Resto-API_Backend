"""Lógica de negocio de reservas (HU-10): solapamientos, aforo y estados.

Reglas:
- Dos reservas activas (status != cancelled) de la misma mesa no pueden
  solaparse: [a_start, a_end) y [b_start, b_end) se solapan si
  a_start < b_end AND b_start < a_end.
- party_size <= dining_tables.capacity.

Los permisos (quién puede tocar qué reserva) se comprueban en el router.
"""

import logging
from datetime import date, datetime, time, timedelta
from html import escape

from sqlalchemy import DateTime, Select, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import FunctionElement

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ReservationConflict,
    UnprocessableError,
)
from app.models.dining_table import DiningTable
from app.models.model_user import User
from app.models.reservation import Reservation
from app.schemas.reservation import ReservationCreate, ReservationUpdate

logger = logging.getLogger(__name__)

CANCELLED = "cancelled"
CONFIRMED = "confirmed"


class reservation_end(FunctionElement):
    """Expresión SQL `reserved_at + duration_min minutos`, según el dialecto."""

    type = DateTime()
    inherit_cache = True
    name = "reservation_end"


@compiles(reservation_end)
def _reservation_end_postgres(element, compiler, **kw) -> str:
    start, minutes = (compiler.process(arg, **kw) for arg in element.clauses)
    return f"({start} + make_interval(mins => {minutes}))"


@compiles(reservation_end, "sqlite")
def _reservation_end_sqlite(element, compiler, **kw) -> str:
    # SQLite guarda los DATETIME como texto 'YYYY-MM-DD HH:MM:SS.ffffff'; se
    # devuelve el mismo formato para que la comparación de cadenas sea correcta.
    start, minutes = (compiler.process(arg, **kw) for arg in element.clauses)
    return (
        f"(strftime('%Y-%m-%d %H:%M:%f', {start}, '+' || {minutes} || ' minutes')"
        " || '000')"
    )


# --- Consultas -------------------------------------------------------------------------


def get_reservation(db: Session, reservation_id: int) -> Reservation:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        logger.warning("Reserva id=%s no encontrada", reservation_id)
        raise NotFoundError(
            f"La reserva {reservation_id} no existe", code="reservation_not_found"
        )
    return reservation


def list_reservations_query(
    *,
    status: str | None = None,
    table_id: int | None = None,
    day: date | None = None,
    user_id: int | None = None,
) -> Select[tuple[Reservation]]:
    """Select de reservas filtrado y ordenado por fecha (se pagina en el router)."""
    stmt = select(Reservation).order_by(Reservation.reserved_at, Reservation.id)
    if status is not None:
        stmt = stmt.where(Reservation.status == status)
    if table_id is not None:
        stmt = stmt.where(Reservation.table_id == table_id)
    if user_id is not None:
        stmt = stmt.where(Reservation.user_id == user_id)
    if day is not None:
        start = datetime.combine(day, time.min)
        stmt = stmt.where(
            Reservation.reserved_at >= start,
            Reservation.reserved_at < start + timedelta(days=1),
        )
    return stmt


def find_overlapping(
    db: Session,
    *,
    table_id: int,
    reserved_at: datetime,
    duration_min: int,
    exclude_id: int | None = None,
) -> Reservation | None:
    """Primera reserva activa de la mesa que se solapa con el intervalo dado."""
    ends_at = reserved_at + timedelta(minutes=duration_min)
    stmt = (
        select(Reservation)
        .where(
            Reservation.table_id == table_id,
            Reservation.status != CANCELLED,
            Reservation.reserved_at < ends_at,
            reservation_end(Reservation.reserved_at, Reservation.duration_min)
            > reserved_at,
        )
        .order_by(Reservation.reserved_at)
        .limit(1)
    )
    if exclude_id is not None:
        stmt = stmt.where(Reservation.id != exclude_id)
    return db.scalar(stmt)


# --- Validaciones ----------------------------------------------------------------------


def _get_table_for_update(db: Session, table_id: int) -> DiningTable:
    """Carga la mesa bloqueando su fila (FOR UPDATE en Postgres).

    El bloqueo serializa las reservas concurrentes de una misma mesa, para que
    dos peticiones simultáneas no pasen a la vez la comprobación de solapamiento.
    """
    table = db.scalar(
        select(DiningTable).where(DiningTable.id == table_id).with_for_update()
    )
    if table is None:
        logger.warning("Mesa id=%s no encontrada al reservar", table_id)
        raise NotFoundError(f"La mesa {table_id} no existe", code="table_not_found")
    return table


def _ensure_capacity(table: DiningTable, party_size: int) -> None:
    if party_size > table.capacity:
        raise UnprocessableError(
            f"La mesa {table.number} admite {table.capacity} personas "
            f"y la reserva es para {party_size}",
            code="party_size_exceeds_capacity",
        )


def _ensure_no_overlap(
    db: Session,
    *,
    table_id: int,
    reserved_at: datetime,
    duration_min: int,
    exclude_id: int | None = None,
) -> None:
    clash = find_overlapping(
        db,
        table_id=table_id,
        reserved_at=reserved_at,
        duration_min=duration_min,
        exclude_id=exclude_id,
    )
    if clash is not None:
        logger.info(
            "Solapamiento en mesa id=%s: %s (+%s min) choca con la reserva id=%s",
            table_id,
            reserved_at,
            duration_min,
            clash.id,
        )
        raise ReservationConflict(
            f"La mesa ya está reservada de {clash.reserved_at:%H:%M} a "
            f"{clash.reserved_at + timedelta(minutes=clash.duration_min):%H:%M} "
            f"del {clash.reserved_at:%d/%m/%Y}"
        )


def ensure_user_exists(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"El usuario {user_id} no existe", code="user_not_found")
    return user


# --- Escrituras ------------------------------------------------------------------------


def create_reservation(
    db: Session, data: ReservationCreate, user_id: int
) -> Reservation:
    """Crea una reserva confirmada para `user_id` validando aforo y solapamiento."""
    try:
        table = _get_table_for_update(db, data.table_id)
        _ensure_capacity(table, data.party_size)
        _ensure_no_overlap(
            db,
            table_id=table.id,
            reserved_at=data.reserved_at,
            duration_min=data.duration_min,
        )
        reservation = Reservation(
            **data.model_dump(exclude={"user_id"}), user_id=user_id, status=CONFIRMED
        )
        db.add(reservation)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(reservation)
    logger.info(
        "Reserva creada id=%s mesa=%s usuario=%s",
        reservation.id,
        reservation.table_id,
        user_id,
    )
    return reservation


def update_reservation(
    db: Session, reservation: Reservation, data: ReservationUpdate
) -> Reservation:
    """Aplica una edición parcial y revalida aforo y solapamiento si hace falta."""
    changes = data.model_dump(exclude_unset=True)
    try:
        table_id = changes.get("table_id", reservation.table_id)
        party_size = changes.get("party_size", reservation.party_size)
        reserved_at = changes.get("reserved_at", reservation.reserved_at)
        duration_min = changes.get("duration_min", reservation.duration_min)
        status = changes.get("status", reservation.status)

        check_capacity = bool({"table_id", "party_size"} & changes.keys())
        # Reactivar una reserva cancelada también vuelve a ocupar el hueco.
        check_overlap = status != CANCELLED and (
            bool({"table_id", "reserved_at", "duration_min"} & changes.keys())
            or reservation.status == CANCELLED
        )
        if check_capacity or check_overlap:
            table = _get_table_for_update(db, table_id)
        if check_capacity:
            _ensure_capacity(table, party_size)
        if check_overlap:
            _ensure_no_overlap(
                db,
                table_id=table_id,
                reserved_at=reserved_at,
                duration_min=duration_min,
                exclude_id=reservation.id,
            )

        for field, value in changes.items():
            setattr(reservation, field, value)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(reservation)
    logger.info("Reserva id=%s editada: %s", reservation.id, sorted(changes))
    return reservation


def cancel_reservation(db: Session, reservation: Reservation) -> Reservation:
    """Cancela una reserva confirmada. Libera el hueco para otras reservas."""
    if reservation.status != CONFIRMED:
        raise ConflictError(
            f"Solo se pueden cancelar reservas confirmadas "
            f"(estado actual: {reservation.status})",
            code="reservation_not_cancellable",
        )
    reservation.status = CANCELLED
    db.commit()
    db.refresh(reservation)
    logger.info("Reserva id=%s cancelada", reservation.id)
    return reservation


def delete_reservation(db: Session, reservation: Reservation) -> None:
    reservation_id = reservation.id
    db.delete(reservation)
    db.commit()
    logger.info("Reserva id=%s borrada", reservation_id)


# --- Notificaciones --------------------------------------------------------------------


def confirmation_email(
    db: Session, reservation: Reservation
) -> tuple[str, str, str] | None:
    """(to, subject, html) del email de confirmación, o None si no hay destinatario."""
    user = db.get(User, reservation.user_id)
    if user is None or not user.email:
        return None
    table = db.get(DiningTable, reservation.table_id)
    table_label = f"mesa {table.number}" if table else f"mesa {reservation.table_id}"
    subject = "Tu reserva está confirmada"
    html = (
        f"<p>Hola {escape(user.name)}:</p>"
        f"<p>Tu reserva del <strong>{reservation.reserved_at:%d/%m/%Y}</strong> a las "
        f"<strong>{reservation.reserved_at:%H:%M}</strong> ({escape(table_label)}, "
        f"{reservation.party_size} personas) está confirmada.</p>"
        "<p>RestoAPI</p>"
    )
    return user.email, subject, html


def cancellation_email(
    db: Session, reservation: Reservation
) -> tuple[str, str, str] | None:
    """(to, subject, html) del email de cancelación, o None si no hay destinatario."""
    user = db.get(User, reservation.user_id)
    if user is None or not user.email:
        return None
    table = db.get(DiningTable, reservation.table_id)
    table_label = f"mesa {table.number}" if table else f"mesa {reservation.table_id}"
    subject = "Tu reserva ha sido cancelada"
    html = (
        f"<p>Hola {escape(user.name)}:</p>"
        f"<p>Tu reserva del <strong>{reservation.reserved_at:%d/%m/%Y}</strong> a las "
        f"<strong>{reservation.reserved_at:%H:%M}</strong> ({escape(table_label)}, "
        f"{reservation.party_size} personas) ha sido cancelada.</p>"
        "<p>RestoAPI</p>"
    )
    return user.email, subject, html
