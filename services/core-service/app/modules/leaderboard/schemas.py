from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class BadgeOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    required_donations: int

    class Config:
        from_attributes = True


class EarnedBadgeOut(BaseModel):
    badge: BadgeOut
    awarded_at: datetime

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    rank: int
    donor_id: int
    user_id: int
    full_name: str
    blood_group: str
    city: Optional[str] = None
    total_donations: int
    reliability_score: float
    badges: List[BadgeOut] = []

    class Config:
        from_attributes = True


class MyRankOut(BaseModel):
    rank: Optional[int]   # None if not ranked yet (no donations)
    donor_id: int
    total_donations: int
    reliability_score: float
    badges: List[BadgeOut] = []
