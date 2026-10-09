import bcrypt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.model_user import User
from app.schemas.schema_user import UserCreate, UserUpdate


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate):
    if get_user_by_email(db, user.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    db_user = User(
        name=user.name,
        email=user.email,
        password_hash=hash_password(user.password),
        phone=user.phone,
        role=user.role.value,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, data: UserUpdate):
    db_user = get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if (
        data.email
        and data.email != db_user.email
        and get_user_by_email(db, data.email)
    ):
        raise HTTPException(status_code=409, detail="Email already registered")

    for field, value in data.model_dump(mode="json", exclude_unset=True).items():
        if field == "password":
            db_user.password_hash = hash_password(value)
        else:
            setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user

def deactivate_user(db: Session, user_id: int):
    db_user = get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.is_active = False
    db.commit()
    db.refresh(db_user)
    return db_user