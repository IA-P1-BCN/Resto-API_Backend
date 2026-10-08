from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import MENU_READ, MENU_WRITE, require_role
from app.crud import crud_category
from app.database import get_db
from app.schemas.schema_category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])

DbSession = Annotated[Session, Depends(get_db)]

READ = [Depends(require_role(*MENU_READ))]
WRITE = [Depends(require_role(*MENU_WRITE))]


@router.post("/", response_model=CategoryOut, status_code=201, dependencies=WRITE)
def create_category(category: CategoryCreate, db: DbSession):
    return crud_category.create_category(db, category)


@router.get("/", response_model=list[CategoryOut], dependencies=READ)
def list_categories(db: DbSession):
    return crud_category.get_categories(db)


@router.get("/{category_id}", response_model=CategoryOut, dependencies=READ)
def get_category(category_id: int, db: DbSession):
    return crud_category.get_category_or_404(db, category_id)


@router.put("/{category_id}", response_model=CategoryOut, dependencies=WRITE)
def update_category(category_id: int, data: CategoryUpdate, db: DbSession):
    return crud_category.update_category(db, category_id, data)


@router.delete("/{category_id}", status_code=204, dependencies=WRITE)
def delete_category(category_id: int, db: DbSession):
    crud_category.delete_category(db, category_id)
