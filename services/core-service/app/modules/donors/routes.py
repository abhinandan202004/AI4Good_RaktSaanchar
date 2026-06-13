from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user, require_roles
from app.modules.donors.repository import DonorRepository
from app.modules.donors.service import DonorService
from app.modules.donors.schemas import DonorProfileCreate, DonorProfileUpdate, DonorOut, DonorListOut
from app.modules.donors.models import BloodGroup
from app.modules.blood_bank.schemas import ValidationReportOut
from app.modules.blood_bank.service import BloodBankService

router = APIRouter(prefix="/donors", tags=["Donors"])


def _svc(db: Session = Depends(get_db)) -> DonorService:
    return DonorService(DonorRepository(db))


@router.post("/me", response_model=DonorOut, status_code=201)
def create_profile(
    data: DonorProfileCreate,
    svc: DonorService = Depends(_svc),
    current_user=Depends(require_roles("donor", "admin")),
):
    return svc.create_profile(current_user.id, data)


@router.get("/me", response_model=DonorOut)
def get_my_profile(
    svc: DonorService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.get_my_profile(current_user.id)


@router.patch("/me", response_model=DonorOut)
def update_my_profile(
    data: DonorProfileUpdate,
    svc: DonorService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.update_my_profile(current_user.id, data)


@router.patch("/me/availability")
def toggle_availability(
    svc: DonorService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.toggle_availability(current_user.id)


@router.get("/", response_model=DonorListOut)
def search_donors(
    blood_group: Optional[BloodGroup] = None,
    city: Optional[str] = None,
    available_only: bool = True,
    skip: int = 0,
    limit: int = 50,
    svc: DonorService = Depends(_svc),
    _=Depends(get_current_user),
):
    return svc.search(blood_group, city, available_only, skip, limit)


@router.get("/leaderboard", response_model=list[DonorOut])
def leaderboard(
    limit: int = 10,
    svc: DonorService = Depends(_svc),
):
    return svc.leaderboard(limit)


@router.get("/{donor_id}", response_model=DonorOut)
def get_donor(
    donor_id: int,
    svc: DonorService = Depends(_svc),
    _=Depends(get_current_user),
):
    return svc.get_profile(donor_id)


def _bank_svc(db: Session = Depends(get_db)) -> BloodBankService:
    from app.modules.blood_bank.repository import BloodBankRepository
    from app.modules.notifications.service import NotificationService
    return BloodBankService(BloodBankRepository(db), NotificationService(db))


@router.get("/me/validation-reports", response_model=list[ValidationReportOut])
def get_my_validation_reports(
    bank_svc: BloodBankService = Depends(_bank_svc),
    current_user=Depends(require_roles("admin", "donor")),
):
    """Retrieve all blood validation and health reports for the authenticated donor."""
    return bank_svc.get_donor_reports(current_user.id)
