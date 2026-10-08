from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import crud_order
from app.database import get_db
from app.schemas.schema_order import OrderCreate, OrderOut, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderOut, status_code=201)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):  # noqa: B008
    return crud_order.create_order(db, order)

@router.get("/", response_model=list[OrderOut])
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

@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):  # noqa: B008
    order = crud_order.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(order_id: int, body: OrderStatusUpdate, db: Session = Depends(get_db)):  # noqa: B008
    return crud_order.update_order_status(db, order_id, body.status)