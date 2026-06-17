from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class TransfusionPredictionCreate(BaseModel):
    age: int = Field(..., ge=2, le=50)
    gender: Literal["Male", "Female"]
    weight_kg: float = Field(..., ge=10.0, le=90.0)
    thalassemia_type: Literal["Major", "Intermedia"]
    current_hb_level: float = Field(..., ge=4.5, le=11.5)
    target_hb_level: float = Field(..., ge=9.0, le=11.0)
    ferritin_level: float = Field(..., ge=100.0, le=5000.0)
    days_since_last_transfusion: int = Field(..., ge=5, le=60)
    previous_units_received: int = Field(..., ge=1, le=4)
    average_units_per_transfusion: float = Field(..., ge=1.0, le=4.0)
    transfusions_last_12_months: int = Field(..., ge=4, le=24)
    spleen_status: Literal["Normal", "Enlarged", "Removed"]
    symptom_severity: Literal["Mild", "Moderate", "Severe"]
    blood_group: Literal["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]


class TransfusionPredictionOut(BaseModel):
    id: int
    user_id: int
    age: int
    gender: str
    weight_kg: float
    thalassemia_type: str
    current_hb_level: float
    target_hb_level: float
    ferritin_level: float
    days_since_last_transfusion: int
    previous_units_received: int
    average_units_per_transfusion: float
    transfusions_last_12_months: int
    spleen_status: str
    symptom_severity: str
    blood_group: str
    predicted_units_required: int
    recommended_next_transfusion_in_days: int
    created_at: datetime

    class Config:
        from_attributes = True
