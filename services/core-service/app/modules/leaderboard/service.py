"""
LeaderboardService
==================
Handles:
  - Leaderboard queries (top donors by total_donations)
  - Badge definitions (seeded on first run)
  - Badge awarding (called after each fulfilled request)
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.modules.donors.models import Donor
from app.modules.leaderboard.models import Badge, DonorBadge
from app.modules.users.models import User


# ── Default badges ─────────────────────────────────────────────────────────────
_DEFAULT_BADGES = [
    {
        "name": "First Drop",
        "description": "Completed your very first blood donation!",
        "icon_url": "🩸",
        "required_donations": 1,
    },
    {
        "name": "Life Saver",
        "description": "Donated blood 5 times — you've saved lives!",
        "icon_url": "💉",
        "required_donations": 5,
    },
    {
        "name": "Blood Hero",
        "description": "10 donations — a true blood hero!",
        "icon_url": "🏅",
        "required_donations": 10,
    },
    {
        "name": "Legend",
        "description": "25 donations — a living legend!",
        "icon_url": "🏆",
        "required_donations": 25,
    },
]


class LeaderboardService:
    def __init__(self, db: Session):
        self.db = db

    # ── Badges ─────────────────────────────────────────────────────────────────

    def seed_badges(self):
        """Idempotent: insert default badges if they don't exist yet."""
        for b in _DEFAULT_BADGES:
            exists = self.db.query(Badge).filter(Badge.name == b["name"]).first()
            if not exists:
                badge = Badge(**b)
                self.db.add(badge)
        self.db.commit()

    def get_all_badges(self) -> List[Badge]:
        return self.db.query(Badge).order_by(Badge.required_donations).all()

    def get_my_badges(self, donor_id: int) -> List[DonorBadge]:
        return (
            self.db.query(DonorBadge)
            .filter(DonorBadge.donor_id == donor_id)
            .all()
        )

    def check_and_award_badges(self, donor_id: int) -> List[Badge]:
        """
        Called after each donation is marked fulfilled.
        Awards any newly-earned badges and returns the newly awarded list.
        """
        donor = self.db.query(Donor).filter(Donor.id == donor_id).first()
        if not donor:
            return []

        all_badges = self.db.query(Badge).all()
        already_earned = {db_row.badge_id for db_row in self.get_my_badges(donor_id)}

        newly_awarded = []
        for badge in all_badges:
            if badge.id in already_earned:
                continue
            if donor.total_donations >= badge.required_donations:
                award = DonorBadge(donor_id=donor_id, badge_id=badge.id)
                self.db.add(award)
                newly_awarded.append(badge)

        if newly_awarded:
            self.db.commit()

        return newly_awarded

    # ── Leaderboard ────────────────────────────────────────────────────────────

    def get_leaderboard(self, limit: int = 20) -> List[dict]:
        """Returns top donors ranked by total_donations desc, then reliability_score desc."""
        donors = (
            self.db.query(Donor)
            .order_by(Donor.total_donations.desc(), Donor.reliability_score.desc())
            .limit(limit)
            .all()
        )

        entries = []
        for rank, donor in enumerate(donors, start=1):
            user = self.db.query(User).filter(User.id == donor.user_id).first()
            badges = [db_row.badge for db_row in self.get_my_badges(donor.id)]
            entries.append({
                "rank": rank,
                "donor_id": donor.id,
                "user_id": donor.user_id,
                "full_name": user.full_name if user else "—",
                "blood_group": donor.blood_group.value,
                "city": donor.city,
                "total_donations": donor.total_donations,
                "reliability_score": donor.reliability_score,
                "badges": badges,
            })

        return entries

    def get_my_rank(self, user_id: int) -> Optional[dict]:
        """Returns the authenticated donor's rank position."""
        donor = self.db.query(Donor).filter(Donor.user_id == user_id).first()
        if not donor:
            return None

        # Count how many donors have more donations
        rank_pos = (
            self.db.query(Donor)
            .filter(Donor.total_donations > donor.total_donations)
            .count()
        ) + 1

        badges = [db_row.badge for db_row in self.get_my_badges(donor.id)]

        return {
            "rank": rank_pos if donor.total_donations > 0 else None,
            "donor_id": donor.id,
            "total_donations": donor.total_donations,
            "reliability_score": donor.reliability_score,
            "badges": badges,
        }
