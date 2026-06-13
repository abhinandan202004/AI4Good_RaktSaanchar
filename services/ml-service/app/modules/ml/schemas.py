from pydantic import BaseModel
from typing import Optional


class DonorRankRequest(BaseModel):
    request_id: Optional[int] = None
    patient_blood_group: Optional[str] = None   # e.g. "A+"
    urgency: Optional[str] = None               # "low" / "medium" / "high" / "critical"
    units_required: int = 1
    patient_city: Optional[str] = None
    patient_latitude: Optional[float] = None
    patient_longitude: Optional[float] = None
    limit: int = 20


class RankedDonorOut(BaseModel):
    donor_id: int
    user_id: int
    blood_group: str
    city: Optional[str]
    is_available: bool
    reliability_score: float
    response_rate: float
    total_donations: int
    blood_group_match: bool
    distance_km: float
    engagement_score: float
    match_probability: float

    class Config:
        from_attributes = True
