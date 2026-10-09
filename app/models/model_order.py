from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("dining_tables.id"))
    waiter_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(20), default="pending")
    total = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    table = relationship("DiningTable", backref="orders")
    waiter = relationship("User", backref="orders")
    items = relationship("OrderItem", backref="order", cascade="all, delete-orphan")
