"""Modelo SQLAlchemy de la tabla `reservations` (HU-10, plan §3.1)."""

from datetime import datetime
from typing import get_args

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.schemas.reservation import ReservationStatus

RESERVATION_STATUSES: tuple[str, ...] = get_args(ReservationStatus)
DEFAULT_DURATION_MIN = 90


class Reservation(Base):
    """Reserva de una mesa por un usuario durante un intervalo de tiempo."""

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("party_size > 0", name="ck_reservations_party_size_positive"),
        CheckConstraint("duration_min > 0", name="ck_reservations_duration_positive"),
        CheckConstraint(
            "status IN ({})".format(", ".join(f"'{s}'" for s in RESERVATION_STATUSES)),
            name="ck_reservations_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    table_id: Mapped[int] = mapped_column(
        ForeignKey("dining_tables.id"), nullable=False, index=True
    )
    reserved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_min: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=DEFAULT_DURATION_MIN,
        server_default=str(DEFAULT_DURATION_MIN),
    )
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="confirmed", server_default="confirmed"
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<Reservation id={self.id} table_id={self.table_id} "
            f"reserved_at={self.reserved_at} status={self.status}>"
        )
