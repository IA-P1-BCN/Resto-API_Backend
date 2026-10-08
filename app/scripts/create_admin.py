"""Crea el primer admin (sin él nadie puede usar /users).

    python -m app.scripts.create_admin EMAIL PASSWORD [NOMBRE]
    docker compose exec api python -m app.scripts.create_admin EMAIL PASSWORD [NOMBRE]
"""
import sys

from sqlalchemy.orm import Session

from app.crud.crud_user import get_user_by_email, hash_password
from app.database import Base, SessionLocal, engine
from app.models.model_user import Role, User


def create_admin(db: Session, email: str, password: str, name: str = "Admin") -> User:
    user = get_user_by_email(db, email)
    if user is None:
        user = User(name=name, email=email, password_hash=hash_password(password))
        db.add(user)
    user.role = Role.admin.value
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def main(argv: list[str]) -> None:
    if len(argv) not in (2, 3):
        sys.exit("Uso: python -m app.scripts.create_admin EMAIL PASSWORD [NOMBRE]")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = create_admin(db, *argv)
        print(f"Admin listo: {user.email} (id {user.id})")


if __name__ == "__main__":
    main(sys.argv[1:])
