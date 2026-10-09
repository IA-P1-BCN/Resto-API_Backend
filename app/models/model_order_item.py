from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Numeric, String

from app.database import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    dish_id = Column(Integer, ForeignKey("dishes.id"))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(8, 2), nullable=False)
    notes = Column(String(255))

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_quantity_positive"),
    )