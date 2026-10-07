from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.jwt import create_access_token
from app.crud import crud_user
from app.database import get_db
from app.models.model_user import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):  # noqa: B008
    """Inicia sesión y devuelve un token JWT."""
    user = crud_user.get_user_by_email(db, form_data.username)
    if not user or not crud_user.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):  # noqa: B008
    """Devuelve los datos del usuario autenticado."""
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "is_active": current_user.is_active,
    }