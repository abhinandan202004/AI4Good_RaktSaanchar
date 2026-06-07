from pydantic import BaseModel


class IronOverloadResponse(BaseModel):

    current_risk: str

    days_until_high_risk: int

    confidence: float

    explanation: str