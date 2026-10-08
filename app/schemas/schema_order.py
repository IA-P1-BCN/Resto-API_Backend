from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


from pydantic import BaseModel


class OrderItemCreate(BaseModel):
    dish_id: int
    quantity: int
    notes: str | None = None

class OrderCreate(BaseModel):
    table_id: int
    items: list[OrderItemCreate]

class OrderItemOut(BaseModel):
    id: int
    dish_id: int
    quantity: int
    unit_price: Decimal
    notes: str | None = None

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: Literal["pending", "in_kitchen", "served", "paid", "cancelled"]


class OrderOut(BaseModel):
    id: int
    table_id: int
    waiter_id: int | None = None
    status: str
    total: Decimal
    created_at: datetime
    updated_at: datetime | None = None
    items: list[OrderItemOut]

    class Config:
        from_attributes = True