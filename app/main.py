from fastapi import FastAPI
from app.database import engine, Base, get_db
from app.models import model_user  # Registrar modelos
from app.routers import router_user

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resto API", version="1.0.0")

app.include_router(router_user.router)

@app.get("/")
def root():
    return {"message": "API Resto working"}
