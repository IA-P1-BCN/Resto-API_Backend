import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token
from app.crud.crud_user import hash_password
from app.database import Base, get_db
from app.main import app
from app.models.model_user import Role, User

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db():
    with TestingSessionLocal() as session:
        yield session

@pytest.fixture
def make_user(db):
    """Crea un usuario con el rol indicado directamente en la BD."""
    def _make(role: Role, email: str | None = None, is_active: bool = True) -> User:
        user = User(
            name=f"{role.value} test",
            email=email or f"{role.value}@test.com",
            password_hash=hash_password("secreto123"),
            role=role.value,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    return _make

@pytest.fixture
def auth_headers(make_user):
    """Cabecera Authorization con el token de un usuario nuevo del rol indicado."""
    def _headers(role: Role) -> dict[str, str]:
        user = make_user(role)
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}
    return _headers

@pytest.fixture
def admin_headers(auth_headers):
    return auth_headers(Role.admin)
