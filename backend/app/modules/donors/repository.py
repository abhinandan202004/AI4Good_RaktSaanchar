from typing import Optional
from sqlalchemy.orm import Session
from app.modules.donors.models import Donor, BloodGroup


class DonorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, donor_id: int) -> Optional[Donor]:
        return self.db.query(Donor).filter(Donor.id == donor_id).first()

    def get_by_user_id(self, user_id: int) -> Optional[Donor]:
        return self.db.query(Donor).filter(Donor.user_id == user_id).first()

    def search(
        self,
        blood_group: Optional[BloodGroup] = None,
        city: Optional[str] = None,
        available_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Donor], int]:
        q = self.db.query(Donor)
        if blood_group:
            q = q.filter(Donor.blood_group == blood_group)
        if city:
            q = q.filter(Donor.city.ilike(f"%{city}%"))
        if available_only:
            q = q.filter(Donor.is_available == True)
        total = q.count()
        return q.offset(skip).limit(limit).all(), total

    def leaderboard(self, limit: int = 10) -> list[Donor]:
        return (
            self.db.query(Donor)
            .order_by(Donor.total_donations.desc(), Donor.reliability_score.desc())
            .limit(limit)
            .all()
        )

    def create(self, **kwargs) -> Donor:
        donor = Donor(**kwargs)
        self.db.add(donor)
        self.db.commit()
        self.db.refresh(donor)
        return donor

    def update(self, donor: Donor, **kwargs) -> Donor:
        for k, v in kwargs.items():
            if v is not None:
                setattr(donor, k, v)
        self.db.commit()
        self.db.refresh(donor)
        return donor
