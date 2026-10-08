from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.database import Base, engine
from app.models import (  # noqa: F401
    dining_table,
    model_category,
    model_dish,
    model_order,
    model_order_item,
    model_user,
    reservation,
)
from app.routers import (
    auth,
    reservations,
    router_category,
    router_dish,
    router_order,
    router_user,
    tables,
    websocket_kitchen,
)

setup_logging()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resto API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip()
                   for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(router_user.router)
app.include_router(router_category.router)
app.include_router(router_dish.router)
app.include_router(router_order.router)
app.include_router(tables.router)
app.include_router(reservations.router)
app.include_router(websocket_kitchen.router)


@app.get("/")
def root():
    return {"message": "API Resto working"}


@app.get("/health")
def health():
    return {"status": "ok"}