from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str = Field(examples=["F-2026-00001"])
    order_id: int
    base_amount: Decimal = Field(examples=["20.00"])
    tax_rate: Decimal = Field(examples=["0.10"])
    tax_amount: Decimal = Field(examples=["2.00"])
    total: Decimal = Field(examples=["22.00"])
    issued_at: datetime
