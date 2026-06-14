from pydantic import BaseModel
from typing import Optional
from app.modules.patients.models import BloodGroup, UrgencyLevel


class MRIReportData(BaseModel):
    heart_t2_star_ms: Optional[float] = None
    liver_t2_star_ms: Optional[float] = None
    liver_iron_concentration_mg_g: Optional[float] = None
    serum_ferritin: Optional[float] = None

    transfusions_last_12_months: Optional[int] = None
    lifetime_transfusions: Optional[int] = None

    chelation_adherence: Optional[str] = None
    chelation_therapy: Optional[str] = None

    age: Optional[int] = None
    weight_kg: Optional[float] = None
    hemoglobin: Optional[float] = None
