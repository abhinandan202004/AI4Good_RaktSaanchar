from pydantic import BaseModel


class FutureRiskPrediction(BaseModel):
    days_until_high_risk: int
    confidence: float
