from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import crud_category
from app.database import get_db
from app.schemas.schema_category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/", response_model=CategoryOut, status_code=201)
def create_category(category: CategoryCreate, db: DbSession):
    return crud_category.create_category(db, category)


@router.get("/", response_model=list[CategoryOut])
def list_categories(db: DbSession):
    return crud_category.get_categories(db)


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: DbSession):
    category = crud_category.get_category(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryUpdate, db: DbSession):
    return crud_category.update_category(db, category_id, data)


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: DbSession):
    crud_category.delete_category(db, category_id)