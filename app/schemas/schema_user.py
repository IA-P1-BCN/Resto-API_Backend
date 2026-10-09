from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.model_user import Role


class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None

class UserCreate(UserBase):
    password: str
    role: Role = Role.customer

class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = None
    role: Role | None = None

class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: Role
    is_active: bool
    created_at: datetime
