from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class TransfusionPrediction(Base):
    __tablename__ = "transfusion_predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    weight_kg = Column(Float, nullable=False)
    thalassemia_type = Column(String, nullable=False)
    current_hb_level = Column(Float, nullable=False)
    target_hb_level = Column(Float, nullable=False)
    ferritin_level = Column(Float, nullable=False)
    days_since_last_transfusion = Column(Integer, nullable=False)
    previous_units_received = Column(Integer, nullable=False)
    average_units_per_transfusion = Column(Float, nullable=False)
    transfusions_last_12_months = Column(Integer, nullable=False)
    spleen_status = Column(String, nullable=False)
    symptom_severity = Column(String, nullable=False)
    blood_group = Column(String, nullable=False)
    predicted_units_required = Column(Integer, nullable=False)
    recommended_next_transfusion_in_days = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User")

    def __repr__(self):
        return f"<TransfusionPrediction id={self.id} user_id={self.user_id} predicted_units={self.predicted_units_required}>"
