from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric, String, Text

from app.database import Base


class Dish(Base):
    __tablename__ = "dishes"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Numeric(8, 2), nullable=False)
    allergens = Column(String(255))
    is_available = Column(Boolean, default=True, nullable=False)
    