from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.modules.users.models import UserRole


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: str
    phone: Optional[str]
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserListOut(BaseModel):
    total: int
    items: list[UserOut]
