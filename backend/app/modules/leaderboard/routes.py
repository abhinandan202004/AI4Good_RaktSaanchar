from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db, get_current_user
from app.modules.leaderboard.service import LeaderboardService
from app.modules.leaderboard.schemas import (
    BadgeOut,
    EarnedBadgeOut,
    LeaderboardEntry,
    MyRankOut,
)

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard & Badges"])


def _svc(db: Session = Depends(get_db)) -> LeaderboardService:
    return LeaderboardService(db)


# ── Leaderboard ────────────────────────────────────────────────────────────────

@router.get("", response_model=list[LeaderboardEntry])
def get_leaderboard(
    limit: int = 20,
    svc: LeaderboardService = Depends(_svc),
):
    """Public endpoint — top donors ranked by total donations."""
    return svc.get_leaderboard(limit=limit)


@router.get("/me", response_model=Optional[MyRankOut])
def get_my_rank(
    svc: LeaderboardService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    """Returns the authenticated donor's position on the leaderboard."""
    return svc.get_my_rank(current_user.id)


# ── Badges ─────────────────────────────────────────────────────────────────────

@router.get("/badges", response_model=list[BadgeOut])
def list_badges(svc: LeaderboardService = Depends(_svc)):
    """Lists all available badges (public)."""
    return svc.get_all_badges()


@router.get("/badges/me", response_model=list[EarnedBadgeOut])
def my_badges(
    svc: LeaderboardService = Depends(_svc),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns all badges earned by the authenticated donor."""
    from app.modules.donors.repository import DonorRepository
    donor = DonorRepository(db).get_by_user_id(current_user.id)
    if not donor:
        return []
    return svc.get_my_badges(donor.id)
