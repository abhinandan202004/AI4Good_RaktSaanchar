from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.donors.models import BloodGroup
from app.modules.blood_bank.models import UnitStatus


# ── Inventory ─────────────────────────────────────────────────────────────────

class InventoryUpsert(BaseModel):
    blood_group: BloodGroup
    quantity_ml: float = Field(..., gt=0, description="Usable millilitres to set/add")


class InventoryOut(BaseModel):
    id: int
    blood_bank_id: int
    blood_group: BloodGroup
    quantity_ml: float
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryListOut(BaseModel):
    items: list[InventoryOut]
    total: int


# ── Blood Units ───────────────────────────────────────────────────────────────

class UnitCheckIn(BaseModel):
    inventory_id: int
    donor_id: Optional[int] = None
    blood_group: BloodGroup
    volume_ml: float = Field(450.0, gt=0)
    collected_at: Optional[datetime] = None
    notes: Optional[str] = None


class UnitQualityUpdate(BaseModel):
    is_safe: bool
    notes: Optional[str] = None


class UnitDispatch(BaseModel):
    request_id: int


class UnitOut(BaseModel):
    id: int
    inventory_id: int
    donor_id: Optional[int]
    blood_group: BloodGroup
    volume_ml: float
    status: UnitStatus
    is_safe: bool
    collected_at: Optional[datetime]
    tested_at: Optional[datetime]
    expiry_date: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Shortage Alert ────────────────────────────────────────────────────────────

class ShortageAlertIn(BaseModel):
    blood_group: BloodGroup
    message: Optional[str] = None


# ── Blood Validation Report ───────────────────────────────────────────────────

class ValidationReportCreate(BaseModel):
    hemoglobin_g_dl: float = Field(..., gt=0)
    systolic_bp: Optional[int] = Field(None, gt=0)
    diastolic_bp: Optional[int] = Field(None, gt=0)
    pulse_bpm: Optional[int] = Field(None, gt=0)
    status: str  # "approved" or "rejected"
    issue_category: Optional[str] = None
    feedback_notes: Optional[str] = None
    improvement_recommendations: Optional[str] = None


class ValidationReportOut(BaseModel):
    id: int
    unit_id: int
    donor_id: int
    hemoglobin_g_dl: float
    systolic_bp: Optional[int]
    diastolic_bp: Optional[int]
    pulse_bpm: Optional[int]
    status: str
    issue_category: Optional[str]
    feedback_notes: Optional[str]
    improvement_recommendations: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Blood Bank Profile ────────────────────────────────────────────────────────

class BloodBankProfileCreate(BaseModel):
    hospital_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None


class BloodBankProfileUpdate(BaseModel):
    hospital_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None


class BloodBankProfileOut(BaseModel):
    id: int
    user_id: int
    hospital_name: str
    latitude: Optional[float]
    longitude: Optional[float]
    contact_phone: Optional[str]
    address: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
