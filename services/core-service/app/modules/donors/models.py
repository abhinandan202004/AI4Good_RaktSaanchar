from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.core.database import Base


class BloodGroup(str, enum.Enum):
    A_pos = "A+"
    A_neg = "A-"
    B_pos = "B+"
    B_neg = "B-"
    AB_pos = "AB+"
    AB_neg = "AB-"
    O_pos = "O+"
    O_neg = "O-"


class Donor(Base):
    __tablename__ = "donors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    blood_group = Column(Enum(BloodGroup), nullable=False)
    age = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)          # kg
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_available = Column(Boolean, default=True)
    last_donated_at = Column(DateTime(timezone=True), nullable=True)

    # Gamification / reliability
    reliability_score = Column(Float, default=1.0)  # 0.0 – 1.0
    response_rate = Column(Float, default=1.0)       # fraction of requests accepted
    no_show_count = Column(Integer, default=0)        # times donor no-showed
    total_donations = Column(Integer, default=0)
    points = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="donor_profile")
    badges = relationship("DonorBadge", back_populates="donor")
    # blood_units relationship will be added in Phase 3 when BloodUnit model is created
    # blood_units = relationship("BloodUnit", back_populates="donor")

    def __repr__(self):
        return f"<Donor id={self.id} blood_group={self.blood_group} score={self.reliability_score}>"
