"""
Blood Request Service â€” core-service microservices version.

Key changes from monolith:
1. NotificationService calls REMOVED â€” replaced by publishing RabbitMQ events.
2. ChatService.get_or_create_room REMOVED â€” chat-service listens to blood_request.accepted.
3. ML ranking REMOVED â€” called via HTTP to ml-service, result embedded in event payload.
4. _haversine_distance and _COMPATIBLE_REVERSE duplicated locally (no cross-service import).
"""
import math
import logging
from typing import Optional

from fastapi import HTTPException, status
from app.modules.blood_requests.repository import BloodRequestRepository
from app.modules.blood_requests.models import RequestStatus, AssignedBy
from app.modules.blood_requests.schemas import BloodRequestCreate, CoordinatorAssign, EscalateRequest
from app.modules.patients.repository import PatientRepository

logger = logging.getLogger(__name__)

# â”€â”€ Shared helpers (duplicated from notifications service) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_COMPATIBLE_REVERSE = {
    "O-":  ["O-"],
    "O+":  ["O-", "O+"],
    "A-":  ["O-", "A-"],
    "A+":  ["O-", "O+", "A-", "A+"],
    "B-":  ["O-", "B-"],
    "B+":  ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
}


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _call_ml_rank_donors(
    blood_group: str, urgency: str, units: int,
    city: Optional[str], lat: Optional[float], lon: Optional[float],
    db=None,  # kept for signature compatibility
    limit: int = 10,
) -> list:
    """Call ml-service POST /predict/donor-ranks (Hugging Face Space). Returns empty list on failure."""
    try:
        import httpx
        import math
        from datetime import datetime, timezone, timedelta
        from app.core.config import settings
        from app.modules.donors.models import Donor
        from sqlalchemy import or_

        if db is None:
            # Cannot query donors without a DB session — return empty
            return []

        # Fetch eligible donors (cooldown 90 days, available)
        cooldown_limit = datetime.now(timezone.utc) - timedelta(days=90)
        donors = (
            db.query(Donor)
            .filter(
                Donor.is_available == True,
                or_(
                    Donor.last_donated_at == None,
                    Donor.last_donated_at <= cooldown_limit
                )
            )
            .all()
        )

        def _days_since(d):
            if d.last_donated_at is None:
                return 365
            return max(90, (datetime.now(timezone.utc) - d.last_donated_at).days)

        donor_features = [
            {
                "donor_id": d.id,
                "user_id": d.user_id,
                "blood_group": d.blood_group.value,
                "city": d.city,
                "is_available": d.is_available,
                "reliability_score": d.reliability_score,
                "response_rate": d.response_rate,
                "no_show_count": d.no_show_count or 0,
                "total_donations": d.total_donations or 0,
                "days_since_last_donation": _days_since(d),
                "latitude": d.latitude,
                "longitude": d.longitude,
            }
            for d in donors
        ]

        payload = {
            "patient_blood_group": blood_group,
            "urgency": urgency,
            "units_required": units,
            "patient_city": city or "",
            "patient_latitude": lat,
            "patient_longitude": lon,
            "donors": donor_features,
            "limit": limit,
        }
        resp = httpx.post(
            f"{settings.ML_SERVICE_URL}/predict/donor-ranks",
            json=payload,
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            # HF Space returns a plain list; guard against old {"donors":[...]} shape
            if isinstance(data, list):
                return data
            return data.get("donors", [])
    except Exception as exc:
        logger.warning("ML service call failed: %s", exc)
    return []



class BloodRequestService:
    def __init__(
        self,
        repo: BloodRequestRepository,
        patient_repo: PatientRepository,
    ):
        self.repo = repo
        self.patient_repo = patient_repo

    def _populate_top_donors(self, req):
        if not req:
            return req
        try:
            # Get patient location for ML ranking
            patient = req.patient
            if patient:
                top = _call_ml_rank_donors(
                    blood_group=req.blood_group.value,
                    urgency=req.urgency,
                    units=req.units_required,
                    city=patient.city,
                    lat=patient.latitude,
                    lon=patient.longitude,
                    db=self.repo.db,
                    limit=10,
                )
            else:
                top = []
            req.top_donors = top
        except Exception:
            req.top_donors = []
        return req

    def _get_or_404(self, req_id: int):
        req = self.repo.get_by_id(req_id)
        if not req:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Blood request not found")
        return self._populate_top_donors(req)

    # â”€â”€ Patient actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def create(self, user_id: int, data: BloodRequestCreate):
        patient = self.patient_repo.get_by_user_id(user_id)
        if not patient:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Create a patient profile first")

        req = self.repo.create(
            patient_id=patient.id,
            blood_group=data.blood_group,
            units_required=data.units_required,
            urgency=data.urgency,
        )

        # Get top donors via ML service
        top_donors = _call_ml_rank_donors(
            blood_group=req.blood_group.value,
            urgency=req.urgency,
            units=req.units_required,
            city=patient.city,
            lat=patient.latitude,
            lon=patient.longitude,
            db=self.repo.db,
            limit=10,
        )
        req.top_donors = top_donors

        # Publish event to RabbitMQ â€” notification-service will handle alerts
        try:
            from app.messaging.publisher import publish_blood_request_created
            publish_blood_request_created(
                request_id=req.id,
                blood_group=req.blood_group.value,
                urgency=req.urgency,
                units_required=req.units_required,
                patient_id=patient.id,
                patient_user_id=patient.user_id,
                patient_city=patient.city,
                patient_lat=patient.latitude,
                patient_lon=patient.longitude,
                hospital=patient.hospital_name or "Local Hospital",
                top_donors=top_donors,
            )
        except Exception as e:
            logger.warning("Failed to publish blood_request.created: %s", e)

        return req

    def get_my_requests(self, user_id: int):
        patient = self.patient_repo.get_by_user_id(user_id)
        if not patient:
            return []
        requests = self.repo.list_by_patient(patient.id)
        for req in requests:
            self._populate_top_donors(req)
        return requests

    def cancel(self, req_id: int, user_id: int):
        req = self._get_or_404(req_id)
        patient = self.patient_repo.get_by_user_id(user_id)
        if not patient or req.patient_id != patient.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your request")
        if req.status not in [RequestStatus.pending, RequestStatus.matched]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Cannot cancel a {req.status.value} request")
        return self.repo.update_status(req, RequestStatus.cancelled)

    def get_status(self, req_id: int):
        req = self._get_or_404(req_id)
        return {"id": req.id, "status": req.status, "assigned_donor_id": req.assigned_donor_id}

    # â”€â”€ Donor actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def accept(self, req_id: int, donor_id: int):
        req = self._get_or_404(req_id)
        if req.assigned_donor_id != donor_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
        if req.status != RequestStatus.matched:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request must be in 'matched' state to accept")

        from app.modules.donors.models import Donor as _Donor
        donor = self.repo.db.query(_Donor).filter(_Donor.id == donor_id).first()
        if donor:
            self._map_to_nearest_blood_bank(req, donor)

        updated = self.repo.update_status(req, RequestStatus.accepted, assigned_blood_bank_id=req.assigned_blood_bank_id)

        # Publish blood_request.accepted â€” chat-service will auto-create room
        try:
            from app.messaging.publisher import publish_blood_request_accepted
            patient_user_id = req.patient.user_id if req.patient else 0
            donor_name = donor.user.full_name if donor and donor.user else ""
            patient_name = req.patient.user.full_name if req.patient and req.patient.user else ""
            publish_blood_request_accepted(
                request_id=req_id,
                donor_user_id=donor.user_id if donor else 0,
                patient_user_id=patient_user_id,
                donor_name=donor_name,
                patient_name=patient_name,
            )
        except Exception as e:
            logger.warning("Failed to publish blood_request.accepted: %s", e)

        return updated

    def reject(self, req_id: int, donor_id: int):
        req = self._get_or_404(req_id)
        if req.assigned_donor_id != donor_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
        return self.repo.update_status(
            req, RequestStatus.pending,
            assigned_donor_id=None, assigned_by=None
        )

    # â”€â”€ Blood bank actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def fulfil(self, req_id: int):
        req = self._get_or_404(req_id)
        if req.status != RequestStatus.accepted:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request must be accepted before fulfilling")
        updated = self.repo.update_status(req, RequestStatus.fulfilled)

        if req.assigned_donor_id:
            from app.modules.donors.models import Donor as _Donor
            donor = self.repo.db.query(_Donor).filter(_Donor.id == req.assigned_donor_id).first()
            if donor:
                donor.total_donations = (donor.total_donations or 0) + 1
                self.repo.db.commit()

                # Award badges
                try:
                    from app.modules.leaderboard.service import LeaderboardService
                    lb_svc = LeaderboardService(self.repo.db)
                    lb_svc.seed_badges()
                    new_badges = lb_svc.check_and_award_badges(donor.id)
                    patient_user_id = req.patient.user_id if req.patient else 0
                    # Publish fulfilled event
                    from app.messaging.publisher import publish_blood_request_fulfilled
                    publish_blood_request_fulfilled(
                        request_id=req_id,
                        donor_user_id=donor.user_id,
                        patient_user_id=patient_user_id,
                        donor_id=donor.id,
                    )
                    if new_badges:
                        from app.messaging.publisher import publish_badge_awarded
                        for badge in new_badges:
                            publish_badge_awarded(donor.user_id, badge.name, badge.icon_url or "ðŸ…")
                except Exception:
                    pass

        return updated

    # â”€â”€ Coordinator actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def assign(self, req_id: int, data: CoordinatorAssign):
        req = self._get_or_404(req_id)
        updated = self.repo.update_status(
            req, RequestStatus.matched,
            assigned_donor_id=data.donor_id,
            assigned_by=AssignedBy.coordinator,
            coordinator_note=data.note,
        )
        # Publish matched event
        try:
            from app.modules.donors.models import Donor as _Donor
            donor = self.repo.db.query(_Donor).filter(_Donor.id == data.donor_id).first()
            from app.messaging.publisher import publish_blood_request_matched
            patient_user_id = req.patient.user_id if req.patient else 0
            publish_blood_request_matched(req_id, donor.user_id if donor else 0, patient_user_id)
        except Exception as e:
            logger.warning("Failed to publish blood_request.matched: %s", e)
        return updated

    def escalate(self, req_id: int, data: EscalateRequest):
        req = self._get_or_404(req_id)
        return self.repo.update_status(req, RequestStatus.escalated, coordinator_note=data.note)

    def list_all(self, skip: int = 0, limit: int = 50):
        items, total = self.repo.list_all(skip, limit)
        return {"total": total, "items": items}

    def list_active(self):
        return self.repo.list_active()

    def accept_open_request(self, req_id: int, donor_id: int):
        req = self._get_or_404(req_id)
        if req.status != RequestStatus.pending:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Request is in '{req.status.value}' state and cannot be accepted.")

        from app.modules.donors.models import Donor as _Donor
        from app.modules.blood_requests.models import BloodRequest as _BloodRequest
        from datetime import datetime, timezone, timedelta

        donor = self.repo.db.query(_Donor).filter(_Donor.id == donor_id).first()
        if not donor:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Donor not found")
        if not donor.is_available:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your donor profile is currently unavailable or deactivated.")
        if donor.last_donated_at and (datetime.now(timezone.utc) - donor.last_donated_at) < timedelta(days=90):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You are currently on a 90-day recovery cooldown.")
        active_assignment = self.repo.db.query(_BloodRequest).filter(
            _BloodRequest.assigned_donor_id == donor.id,
            _BloodRequest.status == RequestStatus.accepted
        ).first()
        if active_assignment:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You are already assigned to an active blood request.")

        compatible_groups = _COMPATIBLE_REVERSE.get(req.blood_group.value, [req.blood_group.value])
        if donor.blood_group.value not in compatible_groups:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Donor blood group {donor.blood_group.value} is not compatible with {req.blood_group.value}.")

        if req.urgency.lower() in ("high", "critical"):
            patient = req.patient
            if patient and patient.latitude is not None and patient.longitude is not None and donor.latitude is not None and donor.longitude is not None:
                dist = _haversine_distance(patient.latitude, patient.longitude, donor.latitude, donor.longitude)
                if dist > 100.0:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Donor is too far ({dist:.2f} km) for this urgent request (max 100 km).")
            elif patient and patient.city and donor.city and patient.city.strip().lower() != donor.city.strip().lower():
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Donor is in a different city and coordinates are missing.")

        self._map_to_nearest_blood_bank(req, donor)

        updated = self.repo.update_status(
            req, RequestStatus.accepted,
            assigned_donor_id=donor_id,
            assigned_by=AssignedBy.coordinator,
            assigned_blood_bank_id=req.assigned_blood_bank_id,
        )

        try:
            from app.messaging.publisher import publish_blood_request_accepted
            patient_user_id = req.patient.user_id if req.patient else 0
            publish_blood_request_accepted(
                request_id=req_id,
                donor_user_id=donor.user_id,
                patient_user_id=patient_user_id,
                donor_name=donor.user.full_name if donor.user else "",
                patient_name=req.patient.user.full_name if req.patient and req.patient.user else "",
            )
        except Exception as e:
            logger.warning("Failed to publish blood_request.accepted: %s", e)

        return updated

    def accept_blood_bank_request(self, req_id: int, blood_bank_user_id: int):
        req = self._get_or_404(req_id)
        if req.status != RequestStatus.pending:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Request is in '{req.status.value}' state and cannot be accepted.")

        if req.urgency.lower() in ("high", "critical"):
            from app.modules.blood_bank.models import BloodBankProfile
            bank_profile = self.repo.db.query(BloodBankProfile).filter(BloodBankProfile.user_id == blood_bank_user_id).first()
            if bank_profile:
                patient = req.patient
                if patient and patient.latitude is not None and patient.longitude is not None and bank_profile.latitude is not None and bank_profile.longitude is not None:
                    dist = _haversine_distance(patient.latitude, patient.longitude, bank_profile.latitude, bank_profile.longitude)
                    if dist > 100.0:
                        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Blood Bank is too far ({dist:.2f} km) for this urgent request.")
                elif patient and patient.city and bank_profile.address and patient.city.strip().lower() not in bank_profile.address.strip().lower():
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Blood Bank is in a different city and coordinates are missing.")

        req.assigned_blood_bank_id = blood_bank_user_id
        req.status = RequestStatus.accepted
        self.repo.db.commit()

        try:
            from app.messaging.publisher import publish_blood_request_accepted
            patient_user_id = req.patient.user_id if req.patient else 0
            publish_blood_request_accepted(req_id, blood_bank_user_id, patient_user_id)
        except Exception as e:
            logger.warning("Failed to publish accepted event: %s", e)

        return req

    def confirm_donation(self, req_id: int, bank_user_id: int):
        req = self._get_or_404(req_id)
        if req.assigned_blood_bank_id != bank_user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to your blood bank")
        if req.status != RequestStatus.accepted:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request must be accepted to confirm donation")

        updated = self.repo.update_status(req, RequestStatus.fulfilled)

        if req.assigned_donor_id:
            from app.modules.donors.models import Donor as _Donor
            donor = self.repo.db.query(_Donor).filter(_Donor.id == req.assigned_donor_id).first()
            if donor:
                from datetime import datetime, timezone
                donor.total_donations = (donor.total_donations or 0) + 1
                donor.last_donated_at = datetime.now(timezone.utc)
                self.repo.db.commit()

                try:
                    from app.modules.leaderboard.service import LeaderboardService
                    lb_svc = LeaderboardService(self.repo.db)
                    lb_svc.seed_badges()
                    new_badges = lb_svc.check_and_award_badges(donor.id)
                    patient_user_id = req.patient.user_id if req.patient else 0
                    from app.messaging.publisher import publish_blood_request_fulfilled
                    publish_blood_request_fulfilled(req_id, donor.user_id, patient_user_id, donor.id)
                    if new_badges:
                        from app.messaging.publisher import publish_badge_awarded
                        for badge in new_badges:
                            publish_badge_awarded(donor.user_id, badge.name, badge.icon_url or "ðŸ…")
                except Exception:
                    pass

        return updated

    def _map_to_nearest_blood_bank(self, req, donor):
        from app.modules.blood_bank.models import BloodBankProfile

        closest_bank = None
        min_dist = float("inf")

        if donor.latitude is not None and donor.longitude is not None:
            banks = self.repo.db.query(BloodBankProfile).all()
            for bank in banks:
                if bank.latitude is not None and bank.longitude is not None:
                    dist = _haversine_distance(donor.latitude, donor.longitude, bank.latitude, bank.longitude)
                    if dist < min_dist:
                        min_dist = dist
                        closest_bank = bank

        if closest_bank is None and req.patient and req.patient.latitude is not None and req.patient.longitude is not None:
            banks = self.repo.db.query(BloodBankProfile).all()
            for bank in banks:
                if bank.latitude is not None and bank.longitude is not None:
                    dist = _haversine_distance(req.patient.latitude, req.patient.longitude, bank.latitude, bank.longitude)
                    if dist < min_dist:
                        min_dist = dist
                        closest_bank = bank

        if closest_bank:
            req.assigned_blood_bank_id = closest_bank.user_id
        else:
            first_bank = self.repo.db.query(BloodBankProfile).first()
            if first_bank:
                req.assigned_blood_bank_id = first_bank.user_id
