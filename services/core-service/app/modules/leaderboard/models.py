from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon_url = Column(String, nullable=True)
    required_donations = Column(Integer, nullable=False)

    donors = relationship("DonorBadge", back_populates="badge")


class DonorBadge(Base):
    __tablename__ = "donor_badges"

    donor_id = Column(Integer, ForeignKey("donors.id"), primary_key=True)
    badge_id = Column(Integer, ForeignKey("badges.id"), primary_key=True)
    awarded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    donor = relationship("Donor", back_populates="badges")
    badge = relationship("Badge", back_populates="donors")
