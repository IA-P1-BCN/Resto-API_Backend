from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

<<<<<<< HEAD
from app.auth.dependencies import get_current_user
from app.auth.jwt import create_access_token
from app.crud import crud_user
from app.database import get_db
from app.models.model_user import User
=======
from app.core.permissions import CurrentUser
from app.core.security import create_access_token
from app.crud import crud_user
from app.database import get_db
from app.schemas.schema_user import UserOut
>>>>>>> 6b0efdc4fd11487e861cdc1dbb171c2f62db3472

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/login")
<<<<<<< HEAD
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):  # noqa: B008
=======
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
>>>>>>> 6b0efdc4fd11487e861cdc1dbb171c2f62db3472
    """Inicia sesión y devuelve un token JWT."""
    user = crud_user.get_user_by_email(db, form_data.username)
    if (
        not user
        or not user.is_active
        or not crud_user.verify_password(form_data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"access_token": create_access_token(user.id), "token_type": "bearer"}

<<<<<<< HEAD
@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):  # noqa: B008
=======

@router.get("/me", response_model=UserOut)
def get_me(current_user: CurrentUser):
>>>>>>> 6b0efdc4fd11487e861cdc1dbb171c2f62db3472
    """Devuelve los datos del usuario autenticado."""
    return current_user
