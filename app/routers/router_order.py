from datetime import date
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import KITCHEN, ORDERS, require_role
from app.crud import crud_order
from app.database import get_db
from app.models.model_user import User
from app.schemas.schema_order import OrderCreate, OrderOut, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])

<<<<<<< HEAD
@router.post("/", response_model=OrderOut, status_code=201)
def create_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),  # noqa: B008
):
    return crud_order.create_order(db, order, background_tasks)
=======
# Sala (admin, waiter) crea los pedidos; sala y cocina los consultan y cambian su estado.
Waiter = Annotated[User, Depends(require_role(*ORDERS))]
STAFF = [Depends(require_role(*ORDERS, *KITCHEN))]
>>>>>>> 7e0f73e6ba82f1e6873f326a30930e8cfc940746

@router.post("/", response_model=OrderOut, status_code=201)
def create_order(
    order: OrderCreate,
    user: Waiter,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),  # noqa: B008
):
    return crud_order.create_order(db, order, background_tasks, waiter_id=user.id)

@router.get("/", response_model=list[OrderOut], dependencies=STAFF)
def list_orders(
    status: str | None = None,
    table_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)  # noqa: B008
):
    return crud_order.get_orders(db, status, table_id, date_from, date_to, skip, limit)

@router.get("/{order_id}", response_model=OrderOut, dependencies=STAFF)
def get_order(order_id: int, db: Session = Depends(get_db)):  # noqa: B008
    order = crud_order.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


<<<<<<< HEAD
@router.patch("/{order_id}/status", response_model=OrderOut)
=======
@router.patch("/{order_id}/status", response_model=OrderOut, dependencies=STAFF)
>>>>>>> 7e0f73e6ba82f1e6873f326a30930e8cfc940746
def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),  # noqa: B008
):
<<<<<<< HEAD
    return crud_order.update_order_status(db, order_id, body.status, background_tasks)
=======
    return crud_order.update_order_status(db, order_id, body.status, background_tasks)
>>>>>>> 7e0f73e6ba82f1e6873f326a30930e8cfc940746
