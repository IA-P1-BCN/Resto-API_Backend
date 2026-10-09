"""Respuestas de las estadísticas (HU-15). Los importes salen como texto con 2 decimales."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SalesDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    orders_count: int = Field(examples=[12])
    total_sales: Decimal = Field(examples=["318.50"])


class SalesSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_from: date | None
    date_to: date | None
    orders_count: int = Field(examples=[48])
    total_sales: Decimal = Field(examples=["1254.00"])
    average_ticket: Decimal = Field(examples=["26.13"])
    daily: list[SalesDayOut]
