from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.model_category import Category
from app.models.model_dish import Dish
from app.schemas.schema_category import CategoryCreate, CategoryUpdate


def get_category(db: Session, category_id: int):
    return db.query(Category).filter(Category.id == category_id).first()

def get_category_by_name(db: Session, name: str):
    return db.query(Category).filter(Category.name == name).first()

def get_categories(db: Session):
    return db.query(Category).order_by(Category.sort_order, Category.name).all()

def create_category(db: Session, category: CategoryCreate):
    if get_category_by_name(db, category.name):
        raise HTTPException(status_code=409, detail="Category already exists")

    db_category = Category(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def update_category(db: Session, category_id: int, data: CategoryUpdate):
    db_category = get_category(db, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")

    if (
        data.name
        and data.name != db_category.name
        and get_category_by_name(db, data.name)
    ):
        raise HTTPException(status_code=409, detail="Category already exists")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(db_category, field, value)

    db.commit()
    db.refresh(db_category)
    return db_category

def delete_category(db: Session, category_id: int):
    db_category = get_category(db, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")

    if db.query(Dish).filter(Dish.category_id == category_id).first():
        raise HTTPException(
            status_code=409, detail="Category has dishes and cannot be deleted"
        )

    db.delete(db_category)
    db.commit()