from fastapi import HTTPException, status
from app.modules.donors.repository import DonorRepository
from app.modules.donors.schemas import DonorProfileCreate, DonorProfileUpdate
from app.modules.donors.models import BloodGroup


class DonorService:
    def __init__(self, repo: DonorRepository):
        self.repo = repo

    def create_profile(self, user_id: int, data: DonorProfileCreate):
        existing = self.repo.get_by_user_id(user_id)
        if existing:
            return self.repo.update(existing, **data.model_dump(exclude_none=True))
        return self.repo.create(user_id=user_id, **data.model_dump())

    def get_profile(self, donor_id: int):
        donor = self.repo.get_by_id(donor_id)
        if not donor:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Donor not found")
        return donor

    def get_my_profile(self, user_id: int):
        donor = self.repo.get_by_user_id(user_id)
        if not donor:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Donor profile not found. Please create one.")
        return donor

    def update_my_profile(self, user_id: int, data: DonorProfileUpdate):
        donor = self.get_my_profile(user_id)
        return self.repo.update(donor, **data.model_dump(exclude_none=True))

    def toggle_availability(self, user_id: int) -> dict:
        donor = self.get_my_profile(user_id)
        donor = self.repo.update(donor, is_available=not donor.is_available)
        return {"is_available": donor.is_available}

    def search(
        self,
        blood_group: BloodGroup = None,
        city: str = None,
        available_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ):
        items, total = self.repo.search(blood_group, city, available_only, skip, limit)
        return {"total": total, "items": items}

    def leaderboard(self, limit: int = 10):
        return self.repo.leaderboard(limit)
