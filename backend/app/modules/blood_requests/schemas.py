from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.modules.blood_requests.models import RequestStatus, AssignedBy
from app.modules.donors.models import BloodGroup


class BloodRequestCreate(BaseModel):
    blood_group: BloodGroup
    units_required: int = 1
    urgency: str = "medium"


from app.modules.patients.schemas import PatientOut
from app.modules.donors.schemas import DonorOut


class BloodRequestOut(BaseModel):
    id: int
    patient_id: int
    blood_group: BloodGroup
    units_required: int
    urgency: str
    status: RequestStatus
    assigned_donor_id: Optional[int]
    assigned_blood_bank_id: Optional[int] = None
    assigned_by: Optional[AssignedBy]
    coordinator_note: Optional[str]
    ai_confidence_score: Optional[float]
    created_at: datetime
    updated_at: datetime
    patient: Optional[PatientOut] = None
    assigned_donor: Optional[DonorOut] = None

    class Config:
        from_attributes = True


class BloodRequestListOut(BaseModel):
    total: int
    items: list[BloodRequestOut]


class CoordinatorAssign(BaseModel):
    donor_id: int
    note: Optional[str] = None


class EscalateRequest(BaseModel):
    note: Optional[str] = None
