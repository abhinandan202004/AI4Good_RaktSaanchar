from fastapi import HTTPException, status
from app.modules.patients.repository import PatientRepository
from app.modules.patients.schemas import PatientProfileCreate, PatientProfileUpdate


class PatientService:
    def __init__(self, repo: PatientRepository):
        self.repo = repo

    def create_profile(self, user_id: int, data: PatientProfileCreate):
        existing = self.repo.get_by_user_id(user_id)
        if existing:
            return self.repo.update(existing, **data.model_dump(exclude_none=True))
        return self.repo.create(user_id=user_id, **data.model_dump())

    def get_my_profile(self, user_id: int):
        patient = self.repo.get_by_user_id(user_id)
        if not patient:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient profile not found. Please create one.")
        return patient

    def update_my_profile(self, user_id: int, data: PatientProfileUpdate):
        patient = self.get_my_profile(user_id)
        return self.repo.update(patient, **data.model_dump(exclude_none=True))
