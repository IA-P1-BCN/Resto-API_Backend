from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.model_order import Order
from app.models.model_order_item import OrderItem
from app.schemas.schema_order import OrderCreate


def create_order(db: Session, order: OrderCreate):
    from app.models.dining_table import DiningTable
    table = db.query(DiningTable).filter(DiningTable.id == order.table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    total = 0
    order_items = []

    for item in order.items:
        from app.models.model_dish import Dish
        dish = db.query(Dish).filter(Dish.id == item.dish_id).first()

        if not dish or not dish.is_available:
            raise HTTPException(status_code=409, detail=f"Dish {item.dish_id} not available")

        unit_price = dish.price
        total += item.quantity * unit_price

        order_items.append({
            "dish_id": item.dish_id,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "notes": item.notes,
        })

    db_order = Order(
        table_id=order.table_id,
        total=total,
        status="pending"
    )
    db.add(db_order)
    db.flush()

    for item_data in order_items:
        db_item = OrderItem(order_id=db_order.id, **item_data)
        db.add(db_item)

    db.commit()
    db.refresh(db_order)
    return db_order

def get_orders(db: Session, status: str | None = None, table_id: int | None = None,
               date_from: str | None = None, date_to: str | None = None,
               skip: int = 0, limit: int = 100):
    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)
    if table_id:
        query = query.filter(Order.table_id == table_id)
    if date_from:
        query = query.filter(Order.created_at >= date_from)
    if date_to:
        query = query.filter(Order.created_at <= date_to)

    return query.offset(skip).limit(limit).all()

def get_order(db: Session, order_id: int):
    return db.query(Order).filter(Order.id == order_id).first()


VALID_TRANSITIONS = {
    "pending": {"in_kitchen", "cancelled"},
    "in_kitchen": {"served", "cancelled"},
    "served": {"paid", "cancelled"},
    "paid": set(),
    "cancelled": set(),
}


def update_order_status(db: Session, order_id: int, new_status: str):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if new_status == order.status:
        return order

    allowed = VALID_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change status from '{order.status}' to '{new_status}'",
        )

    order.status = new_status
    db.commit()
    db.refresh(order)
    return order


