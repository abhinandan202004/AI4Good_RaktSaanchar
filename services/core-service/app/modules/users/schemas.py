from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.modules.users.models import UserRole

class UserOut(BaseModel):
    id: int
    email: EmailStr
    phone: Optional[str] = None
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True
