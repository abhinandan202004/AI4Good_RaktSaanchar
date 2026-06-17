from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user, require_roles
from app.modules.blood_requests.repository import BloodRequestRepository
from app.modules.blood_requests.service import BloodRequestService
from app.modules.blood_requests.schemas import (
    BloodRequestCreate, BloodRequestOut, BloodRequestListOut,
    CoordinatorAssign, EscalateRequest,
)
from app.modules.patients.repository import PatientRepository
from app.modules.donors.repository import DonorRepository


router = APIRouter(prefix="/requests", tags=["Blood Requests"])


def _svc(db: Session = Depends(get_db)) -> BloodRequestService:
    return BloodRequestService(
        BloodRequestRepository(db),
        PatientRepository(db),
    )


def _donor_repo(db: Session = Depends(get_db)) -> DonorRepository:
    return DonorRepository(db)


# â”€â”€ Patient â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/", response_model=BloodRequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    data: BloodRequestCreate,
    svc: BloodRequestService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.create(current_user.id, data)


@router.get("/mine", response_model=list[BloodRequestOut])
def my_requests(
    svc: BloodRequestService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.get_my_requests(current_user.id)


@router.get("/{req_id}/status")
def get_status(
    req_id: int,
    svc: BloodRequestService = Depends(_svc),
    _=Depends(get_current_user),
):
    return svc.get_status(req_id)


@router.patch("/{req_id}/cancel", response_model=BloodRequestOut)
def cancel(
    req_id: int,
    svc: BloodRequestService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.cancel(req_id, current_user.id)


# â”€â”€ Donor â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.patch("/{req_id}/accept", response_model=BloodRequestOut)
def accept(
    req_id: int,
    svc: BloodRequestService = Depends(_svc),
    current_user=Depends(get_current_user),
    donor_repo: DonorRepository = Depends(_donor_repo),
):
    donor = donor_repo.get_by_user_id(current_user.id)
    if not donor:
        from fastapi import HTTPException
        raise HTTPException(404, "Donor profile not found")
    return svc.accept(req_id, donor.id)


@router.patch("/{req_id}/reject", response_model=BloodRequestOut)
def reject(
    req_id: int,
    svc: BloodRequestService = Depends(_svc),
    current_user=Depends(get_current_user),
    donor_repo: DonorRepository = Depends(_donor_repo),
):
    donor = donor_repo.get_by_user_id(current_user.id)
    if not donor:
        from fastapi import HTTPException
        raise HTTPException(404, "Donor profile not found")
    return svc.reject(req_id, donor.id)


@router.patch("/{req_id}/accept-open", response_model=BloodRequestOut)
def accept_open(
    req_id: int,
    svc: BloodRequestService = Depends(_svc),
    current_user=Depends(get_current_user),
    donor_repo: DonorRepository = Depends(_donor_repo),
):
    """
    Direct claim endpoint for any compatible, available donor to accept a pending blood request.
    """
    donor = donor_repo.get_by_user_id(current_user.id)
    if not donor:
        from fastapi import HTTPException
        raise HTTPException(404, "Donor profile not found")
    return svc.accept_open_request(req_id, donor.id)


@router.patch("/{req_id}/accept-bank", response_model=BloodRequestOut)
def accept_bank(
    req_id: int,
    svc: BloodRequestService = Depends(_svc),
    current_user=Depends(require_roles("blood_bank")),
):
    """
    Direct claim endpoint for a blood bank to accept a pending blood request.
    """
    return svc.accept_blood_bank_request(req_id, current_user.id)


# â”€â”€ Blood Bank â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.patch("/{req_id}/fulfil", response_model=BloodRequestOut)
def fulfil(
    req_id: int,
    svc: BloodRequestService = Depends(_svc),
    _=Depends(require_roles("blood_bank", "admin")),
):
    return svc.fulfil(req_id)


@router.patch("/{req_id}/confirm-donation", response_model=BloodRequestOut)
def confirm_donation(
    req_id: int,
    svc: BloodRequestService = Depends(_svc),
    current_user=Depends(require_roles("blood_bank", "admin")),
):
    return svc.confirm_donation(req_id, current_user.id)


# â”€â”€ Coordinator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/", response_model=BloodRequestListOut)
def list_all(
    skip: int = 0,
    limit: int = 50,
    svc: BloodRequestService = Depends(_svc),
    _=Depends(require_roles("admin", "coordinator", "blood_bank", "donor")),
):
    return svc.list_all(skip, limit)


@router.patch("/{req_id}/assign", response_model=BloodRequestOut)
def assign(
    req_id: int,
    data: CoordinatorAssign,
    svc: BloodRequestService = Depends(_svc),
    _=Depends(require_roles("admin", "coordinator")),
):
    return svc.assign(req_id, data)


@router.patch("/{req_id}/escalate", response_model=BloodRequestOut)
def escalate(
    req_id: int,
    data: EscalateRequest,
    svc: BloodRequestService = Depends(_svc),
    _=Depends(require_roles("admin", "coordinator")),
):
    return svc.escalate(req_id, data)


@router.get("/{req_id}", response_model=BloodRequestOut)
def get_request(
    req_id: int,
    svc: BloodRequestService = Depends(_svc),
    _=Depends(get_current_user),
):
    return svc._get_or_404(req_id)
