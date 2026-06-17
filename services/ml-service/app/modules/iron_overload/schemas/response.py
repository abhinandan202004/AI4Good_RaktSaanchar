from pydantic import BaseModel
from typing import Dict, Any


class IronOverloadResponse(BaseModel):
    current_risk: str
    risk_score: float
    days_until_high_risk: int
    explanation: str
    extracted_values: Dict[str, Any]
