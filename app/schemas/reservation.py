"""Esquemas Pydantic de reservas (HU-10).

Sin dependencias de app.core: este módulo es la fuente única de los estados
permitidos y el modelo SQLAlchemy los importa de aquí.
"""

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

ReservationStatus = Literal["confirmed", "cancelled", "completed", "no_show"]
# Estados que se pueden fijar con PATCH; para cancelar está PATCH /{id}/cancel.
EditableReservationStatus = Literal["confirmed", "completed", "no_show"]

MAX_DURATION_MIN = 8 * 60
MAX_NOTES_LENGTH = 500


def _to_naive_utc(value: datetime | None) -> datetime | None:
    """reserved_at es TIMESTAMP sin zona: si llega con zona se pasa a UTC y se quita."""
    if value is not None and value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


class ReservationCreate(BaseModel):
    """Datos para crear una reserva."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "table_id": 3,
                    "reserved_at": "2026-10-10T21:00:00",
                    "duration_min": 90,
                    "party_size": 4,
                    "notes": "Cumpleaños, trona para un bebé",
                }
            ]
        },
    )

    table_id: int = Field(gt=0, description="Mesa reservada.", examples=[3])
    reserved_at: datetime = Field(
        description="Inicio de la reserva. Sin zona horaria; si se envía con zona "
        "se convierte a UTC.",
        examples=["2026-10-10T21:00:00"],
    )
    duration_min: int = Field(
        default=90,
        gt=0,
        le=MAX_DURATION_MIN,
        description="Duración en minutos.",
        examples=[90],
    )
    party_size: int = Field(gt=0, description="Número de personas.", examples=[4])
    notes: str | None = Field(
        default=None, max_length=MAX_NOTES_LENGTH, description="Observaciones."
    )
    user_id: int | None = Field(
        default=None,
        gt=0,
        description="Cliente de la reserva. Solo admin y waiter pueden indicarlo; "
        "si se omite, la reserva es del usuario autenticado.",
    )

    @field_validator("reserved_at")
    @classmethod
    def _normalize_reserved_at(cls, value: datetime | None) -> datetime | None:
        return _to_naive_utc(value)


class ReservationUpdate(BaseModel):
    """Edición parcial de una reserva. Solo se cambian los campos enviados."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"reserved_at": "2026-10-10T22:00:00", "party_size": 5}]
        },
    )

    table_id: int | None = Field(default=None, gt=0, examples=[4])
    reserved_at: datetime | None = Field(default=None, examples=["2026-10-10T22:00:00"])
    duration_min: int | None = Field(default=None, gt=0, le=MAX_DURATION_MIN)
    party_size: int | None = Field(default=None, gt=0, examples=[5])
    notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)
    status: EditableReservationStatus | None = Field(
        default=None,
        description="Solo admin y waiter. Para cancelar se usa "
        "PATCH /reservations/{id}/cancel.",
    )

    @field_validator("reserved_at")
    @classmethod
    def _normalize_reserved_at(cls, value: datetime | None) -> datetime | None:
        return _to_naive_utc(value)

    @model_validator(mode="after")
    def _reject_null_required_fields(self) -> "ReservationUpdate":
        nullable = {"notes"}
        nulls = sorted(
            name
            for name in self.model_fields_set - nullable
            if getattr(self, name) is None
        )
        if nulls:
            raise ValueError(f"Estos campos no pueden ser null: {', '.join(nulls)}")
        return self


class ReservationRead(BaseModel):
    """Reserva tal y como la devuelve la API."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "user_id": 7,
                    "table_id": 3,
                    "reserved_at": "2026-10-10T21:00:00",
                    "duration_min": 90,
                    "ends_at": "2026-10-10T22:30:00",
                    "party_size": 4,
                    "status": "confirmed",
                    "notes": "Cumpleaños, trona para un bebé",
                    "created_at": "2026-10-06T10:15:00",
                }
            ]
        },
    )

    id: int
    user_id: int
    table_id: int
    reserved_at: datetime
    duration_min: int
    party_size: int
    status: ReservationStatus
    notes: str | None
    created_at: datetime | None

    @computed_field(description="Fin de la reserva: reserved_at + duration_min.")
    @property
    def ends_at(self) -> datetime:
        return self.reserved_at + timedelta(minutes=self.duration_min)
