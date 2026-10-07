"""Paginación genérica con el formato {"items", "total", "page", "size"} (§5.2).

TODO(Rita, R-04): revisar límites de size por defecto cuando se cierre HU-11.
"""

from typing import Annotated, Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

ItemT = TypeVar("ItemT", bound=BaseModel)


class Page(BaseModel, Generic[ItemT]):
    """Página de resultados."""

    items: list[ItemT] = Field(description="Elementos de esta página.")
    total: int = Field(description="Número total de elementos.", examples=[42])
    page: int = Field(description="Página actual (empieza en 1).", examples=[1])
    size: int = Field(description="Tamaño de página.", examples=[DEFAULT_PAGE_SIZE])


class PageParams(BaseModel):
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def page_params(
    page: Annotated[
        int, Query(ge=1, description="Número de página (empieza en 1).")
    ] = 1,
    size: Annotated[
        int, Query(ge=1, le=MAX_PAGE_SIZE, description="Elementos por página.")
    ] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    """Dependencia de FastAPI con los query params ?page&size."""
    return PageParams(page=page, size=size)


def paginate(
    db: Session, stmt: Select[Any], params: PageParams, schema: type[ItemT]
) -> Page[ItemT]:
    """Ejecuta `stmt` paginado y convierte cada fila ORM con `schema`."""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.offset(params.offset).limit(params.size)).all()
    return Page[schema](
        items=[schema.model_validate(row) for row in rows],
        total=total or 0,
        page=params.page,
        size=params.size,
    )
