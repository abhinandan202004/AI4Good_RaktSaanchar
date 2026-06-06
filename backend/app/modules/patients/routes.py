from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.modules.patients.repository import PatientRepository
from app.modules.patients.service import PatientService
from app.modules.patients.schemas import PatientProfileCreate, PatientProfileUpdate, PatientOut

router = APIRouter(prefix="/patients", tags=["Patients"])


def _svc(db: Session = Depends(get_db)) -> PatientService:
    return PatientService(PatientRepository(db))


@router.post("/me", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_profile(
    data: PatientProfileCreate,
    svc: PatientService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.create_profile(current_user.id, data)


@router.get("/me", response_model=PatientOut)
def get_my_profile(
    svc: PatientService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.get_my_profile(current_user.id)


@router.patch("/me", response_model=PatientOut)
def update_my_profile(
    data: PatientProfileUpdate,
    svc: PatientService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.update_my_profile(current_user.id, data)
