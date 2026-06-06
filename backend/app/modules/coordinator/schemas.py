from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.modules.blood_requests.models import RequestStatus, AssignedBy
from app.modules.donors.models import BloodGroup


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_requests: int
    pending: int
    matched: int
    accepted: int
    fulfilled: int
    escalated: int
    cancelled: int
    available_donors: int


# ── Override / Manual Assign ──────────────────────────────────────────────────

class ManualAssignIn(BaseModel):
    donor_id: int
    note: Optional[str] = None


class EscalateIn(BaseModel):
    note: Optional[str] = None


# ── Emergency Broadcast ───────────────────────────────────────────────────────

class EmergencyBroadcastIn(BaseModel):
    blood_group: Optional[BloodGroup] = None
    message: str


# ── Request Out (minimal, for coordinator view) ───────────────────────────────

class RequestSummary(BaseModel):
    id: int
    blood_group: BloodGroup
    units_required: int
    urgency: str
    status: RequestStatus
    assigned_donor_id: Optional[int]
    assigned_by: Optional[AssignedBy]
    coordinator_note: Optional[str]
    ai_confidence_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
