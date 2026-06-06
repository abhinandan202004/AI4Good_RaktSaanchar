from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.modules.donors.models import BloodGroup
from app.modules.users.schemas import UserOut


class DonorProfileCreate(BaseModel):
    blood_group: BloodGroup
    age: Optional[int] = None
    weight: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DonorProfileUpdate(BaseModel):
    age: Optional[int] = None
    weight: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_available: Optional[bool] = None


class DonorOut(BaseModel):
    id: int
    user_id: int
    blood_group: BloodGroup
    age: Optional[int]
    weight: Optional[float]
    city: Optional[str]
    state: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    is_available: bool
    reliability_score: float
    total_donations: int
    points: int
    last_donated_at: Optional[datetime]
    user: Optional[UserOut] = None

    class Config:
        from_attributes = True


class DonorListOut(BaseModel):
    total: int
    items: list[DonorOut]
