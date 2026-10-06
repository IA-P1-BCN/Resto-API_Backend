from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.models import model_category, model_dish, model_user  # noqa: F401
from app.routers import router_category, router_user

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resto API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_user.router)
app.include_router(router_category.router)
@app.get("/")
def root():
    return {"message": "API Resto working"}


@app.get("/health")
def health():
    return {"status": "ok"}
