from fastapi import HTTPException, status

from app.modules.blood_bank.repository import BloodBankRepository
from app.modules.blood_bank.models import BloodUnit, UnitStatus
from app.modules.blood_bank.schemas import (
    InventoryUpsert,
    InventoryOut,
    InventoryListOut,
    UnitCheckIn,
    UnitQualityUpdate,
    UnitDispatch,
    UnitOut,
    ShortageAlertIn,
    ValidationReportCreate,
    ValidationReportOut,
    BloodBankProfileCreate,
    BloodBankProfileUpdate,
    BloodBankProfileOut,
)
from app.modules.notifications.service import NotificationService


class BloodBankService:
    def __init__(self, repo: BloodBankRepository, notif_svc: NotificationService):
        self.repo = repo
        self.notif = notif_svc

    # â”€â”€ Inventory â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_inventory(self, blood_bank_id: int) -> InventoryListOut:
        items = self.repo.get_inventory(blood_bank_id)
        return InventoryListOut(
            items=[InventoryOut.model_validate(i) for i in items],
            total=len(items),
        )

    def get_all_inventory(self) -> InventoryListOut:
        items = self.repo.get_all_inventory()
        return InventoryListOut(
            items=[InventoryOut.model_validate(i) for i in items],
            total=len(items),
        )

    def upsert_inventory(
        self, blood_bank_id: int, data: InventoryUpsert
    ) -> InventoryOut:
        inv = self.repo.upsert_inventory(
            blood_bank_id, data.blood_group, data.quantity_ml
        )
        return InventoryOut.model_validate(inv)

    # â”€â”€ Blood Units â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def check_in_unit(self, data: UnitCheckIn) -> UnitOut:
        unit = self.repo.check_in_unit(
            inventory_id=data.inventory_id,
            donor_id=data.donor_id,
            blood_group=data.blood_group,
            volume_ml=data.volume_ml,
            collected_at=data.collected_at,
            notes=data.notes,
        )
        # Also add to aggregate inventory
        self.repo.add_to_inventory(
            blood_bank_id=self._get_bank_id_from_inventory(data.inventory_id),
            blood_group=data.blood_group,
            quantity_ml=data.volume_ml,
        )
        return UnitOut.model_validate(unit)

    def list_units(self, inventory_id: int | None, status: UnitStatus | None) -> list[UnitOut]:
        units = self.repo.list_units(inventory_id, status)
        return [UnitOut.model_validate(u) for u in units]

    def approve_or_reject_unit(
        self, unit_id: int, data: UnitQualityUpdate
    ) -> UnitOut:
        unit = self._get_unit_or_404(unit_id)
        unit = self.repo.update_unit_quality(unit, data.is_safe, data.notes)
        return UnitOut.model_validate(unit)

    def dispatch_unit(self, unit_id: int, data: UnitDispatch) -> UnitOut:
        unit = self._get_unit_or_404(unit_id)
        if not unit.is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unit has not passed quality check â€” cannot dispatch.",
            )
        if unit.status != UnitStatus.available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Unit is currently {unit.status.value}, not available for dispatch.",
            )
        unit = self.repo.dispatch_unit(unit, data.request_id)
        return UnitOut.model_validate(unit)

    # â”€â”€ Shortage Alert â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def broadcast_shortage(self, data: ShortageAlertIn, blood_bank_user_id: int) -> dict:
        msg = data.message or f"Urgent: shortage of {data.blood_group.value} blood!"
        self.notif.broadcast_to_donors(
            blood_group=data.blood_group,
            title=f"ðŸ©¸ Blood Shortage â€” {data.blood_group.value}",
            body=msg,
        )
        # Also publish to Redis for real-time WebSocket delivery
        try:
            import asyncio
            from app.websocket.pubsub import publish_shortage
            asyncio.create_task(publish_shortage(data.blood_group.value, msg))
        except RuntimeError:
            # No running event loop (e.g., in tests) â€” skip pub/sub silently
            pass
        return {"detail": "Shortage alert broadcast successfully."}

    # â”€â”€ Validation Reports â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def submit_validation_report(
        self, unit_id: int, data: ValidationReportCreate, bank_user_id: int
    ) -> ValidationReportOut:
        unit = self._get_unit_or_404(unit_id)
        
        bank_id = self._get_bank_id_from_inventory(unit.inventory_id)
        if bank_id != bank_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this blood unit inventory.",
            )

        if not unit.donor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create validation report for a unit without a donor profile.",
            )

        existing = self.repo.get_validation_report_by_unit(unit_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Validation report already exists for BloodUnit {unit_id}.",
            )

        if data.status not in ("approved", "rejected"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status must be either 'approved' or 'rejected'.",
            )

        report_data = {
            "unit_id": unit_id,
            "donor_id": unit.donor_id,
            "hemoglobin_g_dl": data.hemoglobin_g_dl,
            "systolic_bp": data.systolic_bp,
            "diastolic_bp": data.diastolic_bp,
            "pulse_bpm": data.pulse_bpm,
            "status": data.status,
            "issue_category": data.issue_category,
            "feedback_notes": data.feedback_notes,
            "improvement_recommendations": data.improvement_recommendations,
        }
        report = self.repo.create_validation_report(report_data)

        # Update unit safety and status
        is_safe = (data.status == "approved")
        self.repo.update_unit_quality(unit, is_safe=is_safe, notes=data.feedback_notes)

        # Trigger notification to donor and apply status updates
        from app.modules.donors.models import Donor
        donor = self.repo.db.query(Donor).filter(Donor.id == unit.donor_id).first()
        if donor:
            self.notif.notify_validation_report(donor.user_id, data.status, data.issue_category)
            if is_safe:
                # Award points to the verified donor
                donor.points = (donor.points or 0) + 10
                # Apply 90-day cooldown by setting last_donated_at
                from datetime import datetime, timezone
                donor.last_donated_at = datetime.now(timezone.utc)
                self.repo.db.commit()
                self.notif.send_to_user(
                    donor.user_id,
                    "ðŸŽ–ï¸ Points Earned!",
                    f"Congratulations! Your blood donation has been verified. You earned 10 points! Total points: {donor.points}"
                )
                self.notif.send_to_user(
                    donor.user_id,
                    "â³ Cooldown Period Active",
                    "Your blood donation validation report has been approved. You are now placed on a 90-day recovery cooldown to protect your health. Match acceptance has been disabled."
                )
            else:
                # Deactivate/Flag the donor due to rejected lab report
                donor.is_available = False
                self.repo.db.commit()
                
                # Notify all coordinators
                from app.modules.users.models import User, UserRole
                coordinators = self.repo.db.query(User).filter(User.role == UserRole.coordinator).all()
                donor_name = donor.user.full_name if donor.user else f"Donor #{donor.id}"
                for coord in coordinators:
                    self.notif.send_to_user(
                        coord.id,
                        "ðŸš¨ Donor Health Flag Alert",
                        f"Donor {donor_name} has been flagged/deactivated during blood validation. Reason: {data.issue_category} - {data.feedback_notes or 'No details'}"
                    )

        return ValidationReportOut.model_validate(report)

    def get_validation_report_by_unit(self, unit_id: int, user_role: str, user_id: int) -> ValidationReportOut:
        unit = self._get_unit_or_404(unit_id)
        
        if user_role not in ("admin", "coordinator"):
            if user_role == "blood_bank":
                bank_id = self._get_bank_id_from_inventory(unit.inventory_id)
                if bank_id != user_id:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
            elif user_role == "donor":
                from app.modules.donors.repository import DonorRepository
                donor = DonorRepository(self.repo.db).get_by_user_id(user_id)
                if not donor or unit.donor_id != donor.id:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        report = self.repo.get_validation_report_by_unit(unit_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No validation report found for BloodUnit {unit_id}.",
            )
        return ValidationReportOut.model_validate(report)

    def get_donor_reports(self, user_id: int) -> list[ValidationReportOut]:
        from app.modules.donors.repository import DonorRepository
        donor = DonorRepository(self.repo.db).get_by_user_id(user_id)
        if not donor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor profile not found.")
        reports = self.repo.get_validation_reports_for_donor(donor.id)
        return [ValidationReportOut.model_validate(r) for r in reports]

    def upload_validation_pdf(
        self, report_id: int, file_content: bytes, file_name: str, bank_user_id: int
    ) -> str:
        from app.modules.blood_bank.models import BloodValidationReport
        report = self.repo.db.query(BloodValidationReport).filter(BloodValidationReport.id == report_id).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Validation report {report_id} not found.",
            )

        unit = self._get_unit_or_404(report.unit_id)
        bank_id = self._get_bank_id_from_inventory(unit.inventory_id)
        if bank_id != bank_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this blood unit inventory.",
            )

        if not file_name.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed.",
            )

        import uuid
        import os
        safe_filename = f"report_{report_id}_{uuid.uuid4().hex}.pdf"
        upload_dir = "/app/uploads/validation_reports"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, safe_filename)

        with open(file_path, "wb") as f:
            f.write(file_content)

        report.report_pdf_path = file_path
        self.repo.db.commit()

        return f"/api/v1/blood-bank/validation-reports/{report_id}/pdf"

    def get_validation_pdf_path(self, report_id: int, user_role: str, user_id: int) -> str:
        from app.modules.blood_bank.models import BloodValidationReport
        report = self.repo.db.query(BloodValidationReport).filter(BloodValidationReport.id == report_id).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Validation report {report_id} not found.",
            )

        unit = self._get_unit_or_404(report.unit_id)
        if user_role not in ("admin", "coordinator"):
            if user_role == "blood_bank":
                bank_id = self._get_bank_id_from_inventory(unit.inventory_id)
                if bank_id != user_id:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
            elif user_role == "donor":
                from app.modules.donors.repository import DonorRepository
                donor = DonorRepository(self.repo.db).get_by_user_id(user_id)
                if not donor or report.donor_id != donor.id:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        if not report.report_pdf_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No PDF file has been uploaded for this report.",
            )

        import os
        if not os.path.exists(report.report_pdf_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report PDF file could not be found on disk.",
            )

        return report.report_pdf_path

    # â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _get_unit_or_404(self, unit_id: int) -> BloodUnit:
        unit = self.repo.get_unit(unit_id)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"BloodUnit {unit_id} not found.",
            )
        return unit

    def _get_bank_id_from_inventory(self, inventory_id: int) -> int:
        inv = self.repo.db.query(
            __import__(
                "app.modules.blood_bank.models", fromlist=["BloodInventory"]
            ).BloodInventory
        ).get(inventory_id)
        return inv.blood_bank_id if inv else 0

    # â”€â”€ Blood Bank Profile CRUD & Nearest â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def create_profile(self, user_id: int, data: BloodBankProfileCreate) -> BloodBankProfileOut:
        existing = self.repo.get_profile_by_user_id(user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Blood bank profile already exists for this user."
            )
        profile = self.repo.create_profile(
            user_id=user_id,
            hospital_name=data.hospital_name,
            latitude=data.latitude,
            longitude=data.longitude,
            contact_phone=data.contact_phone,
            address=data.address
        )
        return BloodBankProfileOut.model_validate(profile)

    def get_profile(self, user_id: int) -> BloodBankProfileOut:
        profile = self.repo.get_profile_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blood bank profile not found."
            )
        return BloodBankProfileOut.model_validate(profile)

    def update_profile(self, user_id: int, data: BloodBankProfileUpdate) -> BloodBankProfileOut:
        profile = self.repo.get_profile_by_user_id(user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blood bank profile not found."
            )
        update_dict = data.model_dump(exclude_unset=True)
        updated = self.repo.update_profile(profile, update_dict)
        return BloodBankProfileOut.model_validate(updated)

    def get_nearest_blood_banks(self, lat: float, lon: float, limit: int = 10) -> list[dict]:
        import math
        def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            R = 6371.0
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            return R * c

        profiles = self.repo.get_all_profiles()
        results = []
        for p in profiles:
            if p.latitude is not None and p.longitude is not None:
                dist = haversine_distance(lat, lon, p.latitude, p.longitude)
                results.append({
                    "blood_bank_id": p.user_id,
                    "hospital_name": p.hospital_name,
                    "latitude": p.latitude,
                    "longitude": p.longitude,
                    "contact_phone": p.contact_phone,
                    "address": p.address,
                    "distance_km": round(dist, 2)
                })
        results.sort(key=lambda x: x["distance_km"])
        return results[:limit]
