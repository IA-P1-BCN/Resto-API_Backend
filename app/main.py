from fastapi import FastAPI

from app.database import Base, engine
from app.models import model_user  # noqa: F401  (registra el modelo)
from app.routers import router_user

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resto API", version="1.0.0")

app.include_router(router_user.router)

@app.get("/")
def root():
    return {"message": "API Resto working"}


@app.get("/health")
def health():
    return {"status": "ok"}
