from typing import Optional

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles, get_current_user
from app.modules.blood_bank.repository import BloodBankRepository
from app.modules.blood_bank.models import UnitStatus
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
from app.modules.blood_bank.service import BloodBankService
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="/blood-bank", tags=["Blood Bank"])


def _svc(db: Session = Depends(get_db)) -> BloodBankService:
    notif = NotificationService(db)
    return BloodBankService(BloodBankRepository(db), notif)


# ── Inventory ─────────────────────────────────────────────────────────────────

@router.get("/inventory", response_model=InventoryListOut)
def get_inventory(
    svc: BloodBankService = Depends(_svc),
    current_user=Depends(require_roles("admin", "blood_bank", "coordinator")),
):
    """View all stock (admin / coordinator see all; blood_bank sees their own)."""
    if current_user.role.value == "blood_bank":
        return svc.get_inventory(current_user.id)
    return svc.get_all_inventory()


@router.post("/inventory", response_model=InventoryOut, status_code=status.HTTP_201_CREATED)
def set_inventory(
    data: InventoryUpsert,
    svc: BloodBankService = Depends(_svc),
    current_user=Depends(require_roles("admin", "blood_bank")),
):
    """Set (upsert) stock for a blood group."""
    return svc.upsert_inventory(current_user.id, data)


# ── Blood Units ───────────────────────────────────────────────────────────────

@router.post("/units/check-in", response_model=UnitOut, status_code=status.HTTP_201_CREATED)
def check_in_unit(
    data: UnitCheckIn,
    svc: BloodBankService = Depends(_svc),
    _=Depends(require_roles("admin", "blood_bank")),
):
    """Log a new blood bag arriving at the bank."""
    return svc.check_in_unit(data)


@router.get("/units", response_model=list[UnitOut])
def list_units(
    inventory_id: Optional[int] = None,
    status_filter: Optional[UnitStatus] = None,
    svc: BloodBankService = Depends(_svc),
    _=Depends(require_roles("admin", "blood_bank", "coordinator")),
):
    return svc.list_units(inventory_id, status_filter)


@router.patch("/units/{unit_id}/quality", response_model=UnitOut)
def update_unit_quality(
    unit_id: int,
    data: UnitQualityUpdate,
    svc: BloodBankService = Depends(_svc),
    _=Depends(require_roles("admin", "blood_bank")),
):
    """Approve or reject a blood unit after lab testing."""
    return svc.approve_or_reject_unit(unit_id, data)


@router.patch("/units/{unit_id}/dispatch", response_model=UnitOut)
def dispatch_unit(
    unit_id: int,
    data: UnitDispatch,
    svc: BloodBankService = Depends(_svc),
    _=Depends(require_roles("admin", "blood_bank")),
):
    """Dispatch a safe unit to fulfil a blood request."""
    return svc.dispatch_unit(unit_id, data)


# ── Shortage Alerts ───────────────────────────────────────────────────────────

@router.post("/alerts/shortage")
def broadcast_shortage(
    data: ShortageAlertIn,
    svc: BloodBankService = Depends(_svc),
    current_user=Depends(require_roles("admin", "blood_bank", "coordinator")),
):
    """Broadcast a shortage alert to all available donors of that blood group."""
    return svc.broadcast_shortage(data, current_user.id)


# ── Validation Reports ────────────────────────────────────────────────────

@router.post("/units/{unit_id}/validation-report", response_model=ValidationReportOut, status_code=status.HTTP_201_CREATED)
def submit_validation_report(
    unit_id: int,
    data: ValidationReportCreate,
    svc: BloodBankService = Depends(_svc),
    current_user=Depends(require_roles("admin", "blood_bank")),
):
    """Submit a detailed lab validation report for a blood unit (for donor feedback)."""
    return svc.submit_validation_report(unit_id, data, current_user.id)


@router.get("/units/{unit_id}/validation-report", response_model=ValidationReportOut)
def get_validation_report(
    unit_id: int,
    svc: BloodBankService = Depends(_svc),
    current_user=Depends(require_roles("admin", "blood_bank", "coordinator")),
):
    """Retrieve the validation report associated with a blood unit."""
    return svc.get_validation_report_by_unit(unit_id, current_user.role.value, current_user.id)


@router.post("/validation-reports/{report_id}/pdf")
def upload_validation_report_pdf(
    report_id: int,
    file: UploadFile = File(...),
    svc: BloodBankService = Depends(_svc),
    current_user=Depends(require_roles("admin", "blood_bank")),
):
    """Upload the official lab PDF report file for a blood validation report (Max 10MB)."""
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed.")
    
    # Read file content
    content = file.file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File size exceeds the 10MB limit.")
        
    download_url = svc.upload_validation_pdf(report_id, content, file.filename, current_user.id)
    return {"detail": "PDF report uploaded successfully.", "download_url": download_url}


@router.get("/validation-reports/{report_id}/pdf")
def download_validation_report_pdf(
    report_id: int,
    svc: BloodBankService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    """Download the official lab PDF report file associated with a validation report (secure)."""
    file_path = svc.get_validation_pdf_path(report_id, current_user.role.value, current_user.id)
    return FileResponse(file_path, media_type="application/pdf", filename=f"blood_report_{report_id}.pdf")


# ── Blood Bank Profiles & Nearest ─────────────────────────────────────────────

@router.post("/profile", response_model=BloodBankProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(
    data: BloodBankProfileCreate,
    svc: BloodBankService = Depends(_svc),
    current_user=Depends(require_roles("admin", "blood_bank")),
):
    """Create a profile for the blood bank."""
    return svc.create_profile(current_user.id, data)


@router.get("/profile/me", response_model=BloodBankProfileOut)
def get_profile_me(
    svc: BloodBankService = Depends(_svc),
    current_user=Depends(require_roles("blood_bank")),
):
    """Retrieve the current user's blood bank profile."""
    return svc.get_profile(current_user.id)


@router.patch("/profile/me", response_model=BloodBankProfileOut)
def update_profile_me(
    data: BloodBankProfileUpdate,
    svc: BloodBankService = Depends(_svc),
    current_user=Depends(require_roles("blood_bank")),
):
    """Update the current user's blood bank profile."""
    return svc.update_profile(current_user.id, data)


@router.get("/nearest", response_model=list)
def get_nearest(
    latitude: float,
    longitude: float,
    limit: int = 10,
    svc: BloodBankService = Depends(_svc),
    _=Depends(get_current_user),
):
    """Retrieve the nearest blood banks sorted by distance (Haversine)."""
    return svc.get_nearest_blood_banks(latitude, longitude, limit)
