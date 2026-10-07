"""Pydantic schemas for dining tables (HU-09).

Sin dependencias de app.core: este módulo es la fuente única de los valores
permitidos de location/status, y el modelo SQLAlchemy los importa de aquí.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TableLocation = Literal["indoor", "terrace", "bar"]
TableStatus = Literal["available", "occupied", "reserved", "out_of_service"]


class DiningTableBase(BaseModel):
    """Fields shared by every dining table schema."""

    number: int = Field(
        gt=0,
        description="Table number shown in the dining room. Must be unique.",
        examples=[12],
    )
    capacity: int = Field(
        gt=0,
        description="Maximum number of guests the table can seat.",
        examples=[4],
    )
    location: TableLocation = Field(
        description="Area of the restaurant where the table is placed.",
        examples=["terrace"],
    )


class DiningTableCreate(DiningTableBase):
    """Payload to create a dining table (admin only)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "number": 12,
                    "capacity": 4,
                    "location": "terrace",
                    "status": "available",
                }
            ]
        },
    )

    status: TableStatus = Field(
        default="available",
        description="Initial status. Defaults to `available`.",
        examples=["available"],
    )


class DiningTableUpdate(DiningTableBase):
    """Full replacement of a dining table (PUT, admin only)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "number": 12,
                    "capacity": 6,
                    "location": "indoor",
                    "status": "available",
                }
            ]
        },
    )

    status: TableStatus = Field(
        description="Current status of the table.",
        examples=["available"],
    )


class DiningTableStatusUpdate(BaseModel):
    """Payload to change only the status of a table (PATCH, admin and waiter)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"status": "occupied"}]},
    )

    status: TableStatus = Field(
        description="New status of the table.",
        examples=["occupied"],
    )


class DiningTableRead(DiningTableBase):
    """Dining table as returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "number": 12,
                    "capacity": 4,
                    "location": "terrace",
                    "status": "available",
                }
            ]
        },
    )

    id: int = Field(description="Internal identifier.", examples=[1])
    status: TableStatus = Field(
        description="Current status of the table.", examples=["available"]
    )
