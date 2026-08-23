from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.core.database import Base
from app.modules.donors.models import BloodGroup


class RequestStatus(str, enum.Enum):
    pending = "pending"
    matched = "matched"
    accepted = "accepted"
    fulfilled = "fulfilled"
    cancelled = "cancelled"
    escalated = "escalated"
    validation_failed = "validation_failed"


class AssignedBy(str, enum.Enum):
    ai = "ai"
    coordinator = "coordinator"


class BloodRequest(Base):
    __tablename__ = "blood_requests"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    blood_group = Column(Enum(BloodGroup), nullable=False)
    units_required = Column(Integer, default=1, nullable=False)
    urgency = Column(String, nullable=False)  # mirrors Patient.UrgencyLevel
    status = Column(Enum(RequestStatus), default=RequestStatus.pending, nullable=False)

    # Assignment
    assigned_donor_id = Column(Integer, ForeignKey("donors.id"), nullable=True)
    assigned_blood_bank_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_by = Column(Enum(AssignedBy), nullable=True)
    coordinator_note = Column(Text, nullable=True)
    ai_confidence_score = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    patient = relationship("Patient", backref="blood_requests")
    assigned_donor = relationship("Donor", backref="assigned_requests")
    assigned_blood_bank = relationship("User", foreign_keys=[assigned_blood_bank_id], backref="assigned_requests")
    # chat_room is managed by chat-service and not referenced locally in core-service
    # chat_room = relationship("ChatRoom", back_populates="blood_request", uselist=False)

    def __repr__(self):
        return f"<BloodRequest id={self.id} status={self.status} blood={self.blood_group}>"
