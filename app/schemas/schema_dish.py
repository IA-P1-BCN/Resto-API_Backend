from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DishBase(BaseModel):
    category_id: int
    name: str = Field(max_length=100)
    description: str | None = None
    price: Decimal = Field(ge=0, max_digits=8, decimal_places=2)
    allergens: str | None = Field(default=None, max_length=255)
    is_available: bool = True


class DishCreate(DishBase):
    pass


class DishUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=8, decimal_places=2)
    allergens: str | None = Field(default=None, max_length=255)
    is_available: bool | None = None


class DishOut(DishBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class DishPage(BaseModel):
    items: list[DishOut]
    total: int
    page: int
    size: int