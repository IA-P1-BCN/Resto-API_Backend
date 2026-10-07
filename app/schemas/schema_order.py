from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

class OrderItemCreate(BaseModel):
    dish_id: int
    quantity: int
    notes: Optional[str] = None

class OrderCreate(BaseModel):
    table_id: int
    items: List[OrderItemCreate]

class OrderItemOut(BaseModel):
    id: int
    dish_id: int
    quantity: int
    unit_price: Decimal
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class OrderOut(BaseModel):
    id: int
    table_id: int
    waiter_id: Optional[int] = None
    status: str
    total: Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[OrderItemOut]

    class Config:
        from_attributes = True