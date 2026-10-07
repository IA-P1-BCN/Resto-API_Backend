from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.permissions import MENU_READ, MENU_WRITE, require_role
from app.crud import crud_dish
from app.database import get_db
from app.schemas.schema_dish import DishCreate, DishOut, DishPage, DishUpdate

router = APIRouter(prefix="/dishes", tags=["dishes"])

DbSession = Annotated[Session, Depends(get_db)]

READ = [Depends(require_role(*MENU_READ))]
WRITE = [Depends(require_role(*MENU_WRITE))]


@router.post("/", response_model=DishOut, status_code=201, dependencies=WRITE)
def create_dish(dish: DishCreate, db: DbSession):
    return crud_dish.create_dish(db, dish)


@router.get("/", response_model=DishPage, dependencies=READ)
def list_dishes(
    db: DbSession,
    category_id: int | None = None,
    is_available: bool | None = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return crud_dish.get_dishes(
        db,
        category_id=category_id,
        is_available=is_available,
        max_price=max_price,
        page=page,
        size=size,
    )


@router.get("/{dish_id}", response_model=DishOut, dependencies=READ)
def get_dish(dish_id: int, db: DbSession):
    dish = crud_dish.get_dish(db, dish_id)
    if not dish:
        raise HTTPException(status_code=404, detail="Dish not found")
    return dish


@router.put("/{dish_id}", response_model=DishOut, dependencies=WRITE)
def update_dish(dish_id: int, data: DishUpdate, db: DbSession):
    return crud_dish.update_dish(db, dish_id, data)


@router.delete("/{dish_id}", status_code=204, dependencies=WRITE)
def delete_dish(dish_id: int, db: DbSession):
    crud_dish.delete_dish(db, dish_id)
