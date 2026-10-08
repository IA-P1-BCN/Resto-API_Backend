from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.pagination import Page, PageParams, paginate
from app.crud.crud_category import get_category_or_404
from app.models.model_dish import Dish
from app.schemas.schema_dish import DishCreate, DishOut, DishUpdate


def get_dish(db: Session, dish_id: int):
    return db.query(Dish).filter(Dish.id == dish_id).first()


def get_dish_or_404(db: Session, dish_id: int) -> Dish:
    """Return the dish or raise NotFoundError (404)."""
    db_dish = get_dish(db, dish_id)
    if not db_dish:
        raise NotFoundError("Dish not found")
    return db_dish


def get_dishes(
    db: Session,
    params: PageParams,
    category_id: int | None = None,
    is_available: bool | None = None,
    max_price: Decimal | None = None,
) -> Page[DishOut]:
    stmt = select(Dish)

    if category_id is not None:
        stmt = stmt.where(Dish.category_id == category_id)
    if is_available is not None:
        stmt = stmt.where(Dish.is_available == is_available)
    if max_price is not None:
        stmt = stmt.where(Dish.price <= max_price)

    return paginate(db, stmt.order_by(Dish.id), params, DishOut)


def create_dish(db: Session, dish: DishCreate):
    get_category_or_404(db, dish.category_id)

    db_dish = Dish(**dish.model_dump())
    db.add(db_dish)
    db.commit()
    db.refresh(db_dish)
    return db_dish


def update_dish(db: Session, dish_id: int, data: DishUpdate):
    db_dish = get_dish_or_404(db, dish_id)

    if data.category_id is not None:
        get_category_or_404(db, data.category_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(db_dish, field, value)

    db.commit()
    db.refresh(db_dish)
    return db_dish


def delete_dish(db: Session, dish_id: int):
    db_dish = get_dish_or_404(db, dish_id)

    db.delete(db_dish)
    db.commit()
