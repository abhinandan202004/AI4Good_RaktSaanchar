from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.blood_bank.models import BloodInventory, BloodUnit, UnitStatus, BloodValidationReport, BloodBankProfile
from app.modules.donors.models import BloodGroup


class BloodBankRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Inventory ─────────────────────────────────────────────────────────────

    def get_inventory(self, blood_bank_id: int) -> list[BloodInventory]:
        return (
            self.db.query(BloodInventory)
            .filter(BloodInventory.blood_bank_id == blood_bank_id)
            .all()
        )

    def get_all_inventory(self) -> list[BloodInventory]:
        return self.db.query(BloodInventory).all()

    def get_inventory_by_group(
        self, blood_bank_id: int, blood_group: BloodGroup
    ) -> Optional[BloodInventory]:
        return (
            self.db.query(BloodInventory)
            .filter(
                BloodInventory.blood_bank_id == blood_bank_id,
                BloodInventory.blood_group == blood_group,
            )
            .first()
        )

    def upsert_inventory(
        self, blood_bank_id: int, blood_group: BloodGroup, quantity_ml: float
    ) -> BloodInventory:
        inv = self.get_inventory_by_group(blood_bank_id, blood_group)
        if inv:
            inv.quantity_ml = quantity_ml
            inv.updated_at = datetime.now(timezone.utc)
        else:
            inv = BloodInventory(
                blood_bank_id=blood_bank_id,
                blood_group=blood_group,
                quantity_ml=quantity_ml,
            )
            self.db.add(inv)
        self.db.commit()
        self.db.refresh(inv)
        return inv

    def add_to_inventory(
        self, blood_bank_id: int, blood_group: BloodGroup, quantity_ml: float
    ) -> BloodInventory:
        inv = self.get_inventory_by_group(blood_bank_id, blood_group)
        if inv:
            inv.quantity_ml += quantity_ml
            inv.updated_at = datetime.now(timezone.utc)
        else:
            inv = BloodInventory(
                blood_bank_id=blood_bank_id,
                blood_group=blood_group,
                quantity_ml=quantity_ml,
            )
            self.db.add(inv)
        self.db.commit()
        self.db.refresh(inv)
        return inv

    def deduct_from_inventory(
        self, blood_bank_id: int, blood_group: BloodGroup, quantity_ml: float
    ) -> Optional[BloodInventory]:
        inv = self.get_inventory_by_group(blood_bank_id, blood_group)
        if inv and inv.quantity_ml >= quantity_ml:
            inv.quantity_ml -= quantity_ml
            inv.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(inv)
        return inv

    # ── Blood Units ───────────────────────────────────────────────────────────

    def check_in_unit(
        self,
        inventory_id: int,
        donor_id: Optional[int],
        blood_group: BloodGroup,
        volume_ml: float,
        collected_at: Optional[datetime],
        notes: Optional[str],
    ) -> BloodUnit:
        expiry = datetime.now(timezone.utc) + timedelta(days=42)  # standard shelf life
        unit = BloodUnit(
            inventory_id=inventory_id,
            donor_id=donor_id,
            blood_group=blood_group,
            volume_ml=volume_ml,
            status=UnitStatus.available,
            is_safe=False,                      # awaiting QC
            collected_at=collected_at or datetime.now(timezone.utc),
            expiry_date=expiry,
            notes=notes,
        )
        self.db.add(unit)
        self.db.commit()
        self.db.refresh(unit)
        return unit

    def get_unit(self, unit_id: int) -> Optional[BloodUnit]:
        return self.db.query(BloodUnit).filter(BloodUnit.id == unit_id).first()

    def list_units(
        self,
        inventory_id: Optional[int] = None,
        status: Optional[UnitStatus] = None,
    ) -> list[BloodUnit]:
        q = self.db.query(BloodUnit)
        if inventory_id:
            q = q.filter(BloodUnit.inventory_id == inventory_id)
        if status:
            q = q.filter(BloodUnit.status == status)
        return q.order_by(BloodUnit.expiry_date.asc()).all()

    def update_unit_quality(
        self, unit: BloodUnit, is_safe: bool, notes: Optional[str]
    ) -> BloodUnit:
        unit.is_safe = is_safe
        unit.tested_at = datetime.now(timezone.utc)
        if notes:
            unit.notes = notes
        if not is_safe:
            unit.status = UnitStatus.quarantined
        self.db.commit()
        self.db.refresh(unit)
        return unit

    def dispatch_unit(self, unit: BloodUnit, request_id: int) -> BloodUnit:
        unit.status = UnitStatus.dispatched
        self.db.commit()
        self.db.refresh(unit)
        return unit

    # ── Validation Reports ────────────────────────────────────────────────────

    def create_validation_report(self, report_data: dict) -> BloodValidationReport:
        report = BloodValidationReport(**report_data)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_validation_report_by_unit(self, unit_id: int) -> Optional[BloodValidationReport]:
        return (
            self.db.query(BloodValidationReport)
            .filter(BloodValidationReport.unit_id == unit_id)
            .first()
        )

    def get_validation_reports_for_donor(self, donor_id: int) -> list[BloodValidationReport]:
        return (
            self.db.query(BloodValidationReport)
            .filter(BloodValidationReport.donor_id == donor_id)
            .order_by(BloodValidationReport.created_at.desc())
            .all()
        )

    # ── Blood Bank Profile CRUD ───────────────────────────────────────────────

    def create_profile(self, user_id: int, hospital_name: str, latitude: Optional[float] = None, longitude: Optional[float] = None, contact_phone: Optional[str] = None, address: Optional[str] = None) -> BloodBankProfile:
        profile = BloodBankProfile(
            user_id=user_id,
            hospital_name=hospital_name,
            latitude=latitude,
            longitude=longitude,
            contact_phone=contact_phone,
            address=address,
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_profile_by_user_id(self, user_id: int) -> Optional[BloodBankProfile]:
        return self.db.query(BloodBankProfile).filter(BloodBankProfile.user_id == user_id).first()

    def update_profile(self, profile: BloodBankProfile, update_data: dict) -> BloodBankProfile:
        for key, val in update_data.items():
            if val is not None:
                setattr(profile, key, val)
        profile.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_all_profiles(self) -> list[BloodBankProfile]:
        return self.db.query(BloodBankProfile).all()
