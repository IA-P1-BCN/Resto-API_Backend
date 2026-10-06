from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud.crud_category import get_category
from app.models.model_dish import Dish
from app.schemas.schema_dish import DishCreate, DishUpdate


def get_dish(db: Session, dish_id: int):
    return db.query(Dish).filter(Dish.id == dish_id).first()

def get_dishes(
    db: Session,
    category_id: int | None = None,
    is_available: bool | None = None,
    max_price: Decimal | None = None,
    page: int = 1,
    size: int = 20,
):
    query = db.query(Dish)

    if category_id is not None:
        query = query.filter(Dish.category_id == category_id)
    if is_available is not None:
        query = query.filter(Dish.is_available == is_available)
    if max_price is not None:
        query = query.filter(Dish.price <= max_price)

    total = query.count()
    items = (
        query.order_by(Dish.id)
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "size": size}

def create_dish(db: Session, dish: DishCreate):
    if not get_category(db, dish.category_id):
        raise HTTPException(status_code=404, detail="Category not found")

    db_dish = Dish(**dish.model_dump())
    db.add(db_dish)
    db.commit()
    db.refresh(db_dish)
    return db_dish

def update_dish(db: Session, dish_id: int, data: DishUpdate):
    db_dish = get_dish(db, dish_id)
    if not db_dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    if data.category_id is not None and not get_category(db, data.category_id):
        raise HTTPException(status_code=404, detail="Category not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(db_dish, field, value)

    db.commit()
    db.refresh(db_dish)
    return db_dish

def delete_dish(db: Session, dish_id: int):
    db_dish = get_dish(db, dish_id)
    if not db_dish:
        raise HTTPException(status_code=404, detail="Dish not found")

    db.delete(db_dish)
    db.commit()