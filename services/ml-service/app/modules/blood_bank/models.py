from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import Optional
import enum

from app.core.database import Base
from app.modules.donors.models import BloodGroup


class UnitStatus(str, enum.Enum):
    available   = "available"
    reserved    = "reserved"
    dispatched  = "dispatched"
    quarantined = "quarantined"
    expired     = "expired"


class BloodInventory(Base):
    """Aggregate units per blood group held by a blood-bank user."""
    __tablename__ = "blood_inventory"

    id            = Column(Integer, primary_key=True, index=True)
    blood_bank_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    blood_group   = Column(Enum(BloodGroup), nullable=False)
    quantity_ml   = Column(Float, default=0.0)           # total usable ml
    updated_at    = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    blood_bank = relationship("User", foreign_keys=[blood_bank_id])
    units      = relationship("BloodUnit", back_populates="inventory",
                              cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BloodInventory bank={self.blood_bank_id} group={self.blood_group} qty={self.quantity_ml}ml>"


class BloodUnit(Base):
    """Individual blood bag / unit tracked by the system."""
    __tablename__ = "blood_units"

    id            = Column(Integer, primary_key=True, index=True)
    inventory_id  = Column(Integer, ForeignKey("blood_inventory.id"), nullable=False)
    donor_id      = Column(Integer, ForeignKey("donors.id"), nullable=True)
    blood_group   = Column(Enum(BloodGroup), nullable=False)
    volume_ml     = Column(Float, default=450.0)
    status        = Column(Enum(UnitStatus), default=UnitStatus.available, nullable=False)
    is_safe       = Column(Boolean, default=False)        # lab-tested
    collected_at  = Column(DateTime(timezone=True), nullable=True)
    tested_at     = Column(DateTime(timezone=True), nullable=True)
    expiry_date   = Column(DateTime(timezone=True), nullable=True)
    notes         = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))

    inventory = relationship("BloodInventory", back_populates="units")
    donor     = relationship("Donor", foreign_keys=[donor_id])
    validation_report = relationship("BloodValidationReport", back_populates="unit", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BloodUnit id={self.id} group={self.blood_group} status={self.status}>"


class BloodValidationReport(Base):
    """Lab validation and donor health report for a blood unit."""
    __tablename__ = "blood_validation_reports"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("blood_units.id", ondelete="CASCADE"), nullable=False, unique=True)
    donor_id = Column(Integer, ForeignKey("donors.id", ondelete="CASCADE"), nullable=False)
    
    # Lab metrics
    hemoglobin_g_dl = Column(Float, nullable=False)
    systolic_bp = Column(Integer, nullable=True)
    diastolic_bp = Column(Integer, nullable=True)
    pulse_bpm = Column(Integer, nullable=True)
    
    # Results & issues
    status = Column(String, nullable=False)  # "approved" or "rejected"
    issue_category = Column(String, nullable=True)  # "low_hemoglobin", "blood_pressure", "infectious_disease", "other"
    feedback_notes = Column(Text, nullable=True)
    improvement_recommendations = Column(Text, nullable=True)
    report_pdf_path = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    unit = relationship("BloodUnit", back_populates="validation_report")
    donor = relationship("Donor", foreign_keys=[donor_id])

    @property
    def report_pdf_url(self) -> Optional[str]:
        if self.report_pdf_path:
            return f"/api/v1/blood-bank/validation-reports/{self.id}/pdf"
        return None

    def __repr__(self):
        return f"<BloodValidationReport id={self.id} unit_id={self.unit_id} status={self.status}>"


class BloodBankProfile(Base):
    __tablename__ = "blood_bank_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    hospital_name = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    contact_phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="blood_bank_profile")

    def __repr__(self):
        return f"<BloodBankProfile id={self.id} hospital_name={self.hospital_name}>"
