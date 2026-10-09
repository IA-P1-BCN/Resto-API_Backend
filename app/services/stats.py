"""Estadísticas de ventas y platos más vendidos (HU-15).

Cuenta como venta todo pedido en estado `served` o `paid`. Los `pending` e
`in_kitchen` todavía no son venta y los `cancelled` no lo son nunca.

Las fechas `date_from` y `date_to` filtran por la fecha de creación del pedido y
las dos están incluidas.

Caché: cada resultado se guarda `STATS_CACHE_TTL` segundos (60 por defecto) en
memoria, con una entrada por combinación de parámetros. Durante ese tiempo las
ventas nuevas no se ven. Con `STATS_CACHE_TTL=0` no se guarda nada.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from threading import Lock

from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.model_dish import Dish
from app.models.model_order import Order
from app.models.model_order_item import OrderItem

SALE_STATUSES = ("served", "paid")
CENT = Decimal("0.01")
ZERO = Decimal("0.00")

_sales_cache: TTLCache = TTLCache(maxsize=128, ttl=settings.STATS_CACHE_TTL)
_top_dishes_cache: TTLCache = TTLCache(
    maxsize=128, ttl=settings.STATS_CACHE_TTL)
_cache_lock = Lock()


def clear_cache() -> None:
    """Vacía las cachés de estadísticas (la usan los tests)."""
    with _cache_lock:
        _sales_cache.clear()
        _top_dishes_cache.clear()


@dataclass(frozen=True)
class SalesDay:
    day: date
    orders_count: int
    total_sales: Decimal


@dataclass(frozen=True)
class SalesSummary:
    date_from: date | None
    date_to: date | None
    orders_count: int
    total_sales: Decimal
    average_ticket: Decimal
    daily: tuple[SalesDay, ...]


@dataclass(frozen=True)
class TopDish:
    dish_id: int
    name: str
    quantity: int
    revenue: Decimal


def _money(value: object) -> Decimal:
    """Importe con 2 decimales. SUM devuelve None si no hay filas."""
    return Decimal(str(value or 0)).quantize(CENT)


def _as_date(value: object) -> date:
    """func.date() devuelve un date en Postgres y un texto 'YYYY-MM-DD' en SQLite."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _sales_filter(
    stmt: Select, date_from: date | None, date_to: date | None
) -> Select:
    """Solo pedidos que son venta y, si se indican, dentro del rango de fechas."""
    stmt = stmt.where(Order.status.in_(SALE_STATUSES))
    if date_from is not None:
        stmt = stmt.where(Order.created_at >=
                          datetime.combine(date_from, time.min))
    if date_to is not None:
        next_day = datetime.combine(date_to + timedelta(days=1), time.min)
        stmt = stmt.where(Order.created_at < next_day)
    return stmt


@cached(
    _sales_cache,
    key=lambda db, date_from=None, date_to=None: hashkey(date_from, date_to),
    lock=_cache_lock,
)
def sales_summary(
    db: Session, date_from: date | None = None, date_to: date | None = None
) -> SalesSummary:
    """Número de pedidos, total vendido, ticket medio y desglose por día."""
    day = func.date(Order.created_at)
    stmt = _sales_filter(
        select(day, func.count(Order.id), func.sum(Order.total)),
        date_from,
        date_to,
    )
    rows = db.execute(stmt.group_by(day).order_by(day)).all()

    daily = tuple(
        SalesDay(day=_as_date(d), orders_count=count,
                 total_sales=_money(total))
        for d, count, total in rows
    )
    orders_count = sum(d.orders_count for d in daily)
    total_sales = sum((d.total_sales for d in daily), ZERO)
    average_ticket = (
        total_sales / orders_count).quantize(CENT) if orders_count else ZERO
    return SalesSummary(
        date_from=date_from,
        date_to=date_to,
        orders_count=orders_count,
        total_sales=total_sales,
        average_ticket=average_ticket,
        daily=daily,
    )


@cached(
    _top_dishes_cache,
    key=lambda db, date_from=None, date_to=None, limit=5: hashkey(
        date_from, date_to, limit
    ),
    lock=_cache_lock,
)
def top_dishes(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 5,
) -> tuple[TopDish, ...]:
    """Platos más vendidos por unidades. Empate: más ingresos y luego menor id."""
    quantity = func.sum(OrderItem.quantity)
    revenue = func.sum(OrderItem.quantity * OrderItem.unit_price)
    stmt = _sales_filter(
        select(Dish.id, Dish.name, quantity, revenue)
        .join(OrderItem, OrderItem.dish_id == Dish.id)
        .join(Order, Order.id == OrderItem.order_id),
        date_from,
        date_to,
    )
    stmt = (
        stmt.group_by(Dish.id, Dish.name)
        .order_by(quantity.desc(), revenue.desc(), Dish.id)
        .limit(limit)
    )
    return tuple(
        TopDish(dish_id=dish_id, name=name,
                quantity=int(qty), revenue=_money(rev))
        for dish_id, name, qty, rev in db.execute(stmt).all()
    )
