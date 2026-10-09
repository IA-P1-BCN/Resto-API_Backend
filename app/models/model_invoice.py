from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import backref, relationship

from app.database import Base


class Invoice(Base):
    """Factura de un pedido servido (HU-14). Una factura por pedido."""

    __tablename__ = "invoices"
    __table_args__ = (
        # El número correlativo se reinicia cada año: (2026, 1), (2026, 2)... (2027, 1).
        UniqueConstraint("year", "sequence", name="uq_invoices_year_sequence"),
        CheckConstraint("total >= 0", name="ck_invoices_total_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(20), unique=True, nullable=False)  # F-2026-00001
    year = Column(Integer, nullable=False)
    sequence = Column(Integer, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"),
                      unique=True, nullable=False)
    base_amount = Column(Numeric(10, 2), nullable=False)
    tax_rate = Column(Numeric(4, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    issued_at = Column(DateTime, nullable=False, server_default=func.now())

    order = relationship("Order", backref=backref("invoice", uselist=False))
