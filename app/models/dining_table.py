"""SQLAlchemy model for the `dining_tables` table (HU-09, plan §3.1).

Se llama dining_tables porque `table` es palabra reservada de SQL.
"""

from typing import get_args

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

# ASSUMPTION: app.core.database expone `Base` (DeclarativeBase de SQLAlchemy 2.0) — Carla, C-01.
from app.core.database import Base
from app.schemas.dining_table import TableLocation, TableStatus

TABLE_LOCATIONS: tuple[str, ...] = get_args(TableLocation)
TABLE_STATUSES: tuple[str, ...] = get_args(TableStatus)


def _in_list(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class DiningTable(Base):
    """A physical table in the dining room."""

    __tablename__ = "dining_tables"
    # ASSUMPTION: Base no define naming_convention para "ck"; si la define con
    # %(constraint_name)s, estos nombres quedarían duplicados (ck_dining_tables_ck_...).
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_dining_tables_capacity_positive"),
        CheckConstraint(
            _in_list("location", TABLE_LOCATIONS), name="ck_dining_tables_location"
        ),
        CheckConstraint(
            _in_list("status", TABLE_STATUSES), name="ck_dining_tables_status"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available", server_default="available"
    )

    def __repr__(self) -> str:
        return f"<DiningTable id={self.id} number={self.number} status={self.status}>"
