from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.modules.patients.models import BloodGroup, UrgencyLevel
from app.modules.users.schemas import UserOut


class PatientProfileCreate(BaseModel):
    blood_group_required: BloodGroup
    units_required: int = 1
    urgency: UrgencyLevel = UrgencyLevel.medium
    hospital_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    medical_notes: Optional[str] = None
    needed_by: Optional[datetime] = None


class PatientProfileUpdate(BaseModel):
    units_required: Optional[int] = None
    urgency: Optional[UrgencyLevel] = None
    hospital_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    medical_notes: Optional[str] = None
    needed_by: Optional[datetime] = None


class PatientOut(BaseModel):
    id: int
    user_id: int
    blood_group_required: BloodGroup
    units_required: int
    urgency: UrgencyLevel
    hospital_name: Optional[str]
    city: Optional[str]
    state: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    is_fulfilled: bool
    needed_by: Optional[datetime]
    user: Optional[UserOut] = None

    class Config:
        from_attributes = True
