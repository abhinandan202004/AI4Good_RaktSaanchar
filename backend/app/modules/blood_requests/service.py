from typing import Optional

from fastapi import HTTPException, status
from app.modules.blood_requests.repository import BloodRequestRepository
from app.modules.blood_requests.models import RequestStatus, AssignedBy
from app.modules.blood_requests.schemas import BloodRequestCreate, CoordinatorAssign, EscalateRequest
from app.modules.patients.repository import PatientRepository
from app.modules.notifications.service import NotificationService


class BloodRequestService:
    def __init__(
        self,
        repo: BloodRequestRepository,
        patient_repo: PatientRepository,
        notif: Optional[NotificationService] = None,
    ):
        self.repo = repo
        self.patient_repo = patient_repo
        self.notif = notif  # optional so existing callers that don't pass it still work

    def _populate_top_donors(self, req):
        if not req:
            return req
        try:
            from app.modules.ml import service as ml_service
            req.top_donors = ml_service.rank_donors(
                db=self.repo.db,
                request_id=req.id,
                limit=10
            )
        except Exception:
            req.top_donors = []
        return req

    def _get_or_404(self, req_id: int):
        req = self.repo.get_by_id(req_id)
        if not req:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Blood request not found")
        return self._populate_top_donors(req)

    # ── Patient actions ───────────────────────────────────────────────────────

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
        if self.notif:
            self.notif.notify_request_created(req)
        return self._populate_top_donors(req)

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
        # Verify ownership via patient profile
        patient = self.patient_repo.get_by_user_id(user_id)
        if not patient or req.patient_id != patient.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your request")
        if req.status not in [RequestStatus.pending, RequestStatus.matched]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Cannot cancel a {req.status.value} request")
        return self.repo.update_status(req, RequestStatus.cancelled)

    def get_status(self, req_id: int):
        req = self._get_or_404(req_id)
        return {"id": req.id, "status": req.status, "assigned_donor_id": req.assigned_donor_id}

    # ── Donor actions ─────────────────────────────────────────────────────────

    def accept(self, req_id: int, donor_id: int):
        req = self._get_or_404(req_id)
        if req.assigned_donor_id != donor_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
        if req.status != RequestStatus.matched:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request must be in 'matched' state to accept")
        updated = self.repo.update_status(req, RequestStatus.accepted)

        # Notify both parties
        if self.notif and req.patient:
            from app.modules.donors.models import Donor as _Donor
            donor = self.repo.db.query(_Donor).filter(_Donor.id == donor_id).first()
            if donor:
                self.notif.notify_request_accepted(req.patient.user_id, donor.user_id)

        # Auto-create chat room for donor ↔ patient communication
        try:
            from app.modules.chat.service import ChatService
            ChatService(self.repo.db).get_or_create_room(request_id=req_id)
        except Exception:
            pass  # Chat room creation failure must not block the accept flow

        return updated

    def reject(self, req_id: int, donor_id: int):
        req = self._get_or_404(req_id)
        if req.assigned_donor_id != donor_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request is not assigned to you")
        return self.repo.update_status(
            req, RequestStatus.pending,
            assigned_donor_id=None, assigned_by=None
        )

    # ── Blood bank actions ────────────────────────────────────────────────────

    def fulfil(self, req_id: int):
        req = self._get_or_404(req_id)
        if req.status != RequestStatus.accepted:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Request must be accepted before fulfilling")
        updated = self.repo.update_status(req, RequestStatus.fulfilled)

        if req.assigned_donor_id:
            from app.modules.donors.models import Donor as _Donor
            donor = self.repo.db.query(_Donor).filter(_Donor.id == req.assigned_donor_id).first()
            if donor:
                # Increment donation count
                donor.total_donations = (donor.total_donations or 0) + 1
                self.repo.db.commit()

                # Send fulfillment notifications
                if self.notif and req.patient:
                    self.notif.notify_request_fulfilled(req.patient.user_id, donor.user_id)

                # Award badges and notify donor of any new ones
                try:
                    from app.modules.leaderboard.service import LeaderboardService
                    lb_svc = LeaderboardService(self.repo.db)
                    lb_svc.seed_badges()  # idempotent — ensures badges exist
                    new_badges = lb_svc.check_and_award_badges(donor.id)
                    if self.notif and new_badges:
                        for badge in new_badges:
                            self.notif.notify_badge_awarded(donor.user_id, badge.name, badge.icon_url)
                except Exception:
                    pass  # Badge awarding failure must not block the fulfil flow

        return updated

    # ── Coordinator actions ───────────────────────────────────────────────────

    def assign(self, req_id: int, data: CoordinatorAssign):
        req = self._get_or_404(req_id)
        return self.repo.update_status(
            req, RequestStatus.matched,
            assigned_donor_id=data.donor_id,
            assigned_by=AssignedBy.coordinator,
            coordinator_note=data.note,
        )

    def escalate(self, req_id: int, data: EscalateRequest):
        req = self._get_or_404(req_id)
        return self.repo.update_status(
            req, RequestStatus.escalated,
            coordinator_note=data.note,
        )

    def list_all(self, skip: int = 0, limit: int = 50):
        items, total = self.repo.list_all(skip, limit)
        return {"total": total, "items": items}

    def list_active(self):
        return self.repo.list_active()

    def accept_open_request(self, req_id: int, donor_id: int):
        req = self._get_or_404(req_id)
        if req.status != RequestStatus.pending:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Request is in '{req.status.value}' state and cannot be accepted.")
        
        # Check compatibility
        from app.modules.donors.models import Donor as _Donor
        from app.modules.notifications.service import _COMPATIBLE_REVERSE
        donor = self.repo.db.query(_Donor).filter(_Donor.id == donor_id).first()
        if not donor:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Donor not found")
            
        compatible_groups = _COMPATIBLE_REVERSE.get(req.blood_group.value, [req.blood_group.value])
        if donor.blood_group.value not in compatible_groups:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Donor blood group {donor.blood_group.value} is not compatible with request blood group {req.blood_group.value}.")

        # Check distance if urgent
        if req.urgency.lower() in ("high", "critical"):
            from app.modules.notifications.service import _haversine_distance
            patient = req.patient
            if patient and patient.latitude is not None and patient.longitude is not None and donor.latitude is not None and donor.longitude is not None:
                dist = _haversine_distance(patient.latitude, patient.longitude, donor.latitude, donor.longitude)
                if dist > 100.0:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Donor is too far ({dist:.2f} km) to accept this urgent request (maximum allowed is 100 km).")
            elif patient and patient.city and donor.city and patient.city.strip().lower() != donor.city.strip().lower():
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Donor is in a different city and coordinates are missing.")

        # Assign and accept
        updated = self.repo.update_status(
            req, RequestStatus.accepted,
            assigned_donor_id=donor_id,
            assigned_by=AssignedBy.coordinator,
        )

        if self.notif and req.patient:
            self.notif.send_to_user(
                req.patient.user_id,
                "💚 Donor Accepted Urgent Request",
                f"Donor {donor.user.full_name if donor.user else 'Hero'} has accepted your urgent blood request!",
            )
            self.notif.send_to_user(
                donor.user_id,
                "💚 Request Accepted Successfully",
                "You have accepted the blood donation request. Please report to the hospital.",
            )

        # Auto-create chat room for donor ↔ patient communication
        try:
            from app.modules.chat.service import ChatService
            ChatService(self.repo.db).get_or_create_room(request_id=req_id)
        except Exception:
            pass  # Chat room creation failure must not block the accept flow

        return updated

    def accept_blood_bank_request(self, req_id: int, blood_bank_user_id: int):
        req = self._get_or_404(req_id)
        if req.status != RequestStatus.pending:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Request is in '{req.status.value}' state and cannot be accepted.")
        
        # Check distance if urgent
        if req.urgency.lower() in ("high", "critical"):
            from app.modules.notifications.service import _haversine_distance
            from app.modules.blood_bank.models import BloodBankProfile
            bank_profile = self.repo.db.query(BloodBankProfile).filter(BloodBankProfile.user_id == blood_bank_user_id).first()
            if bank_profile:
                patient = req.patient
                if patient and patient.latitude is not None and patient.longitude is not None and bank_profile.latitude is not None and bank_profile.longitude is not None:
                    dist = _haversine_distance(patient.latitude, patient.longitude, bank_profile.latitude, bank_profile.longitude)
                    if dist > 100.0:
                        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Blood Bank is too far ({dist:.2f} km) to accept this urgent request (maximum allowed is 100 km).")
                elif patient and patient.city and bank_profile.address and patient.city.strip().lower() not in bank_profile.address.strip().lower():
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Blood Bank is in a different city and coordinates are missing.")

        # Assign to blood bank
        req.assigned_blood_bank_id = blood_bank_user_id
        req.status = RequestStatus.accepted
        self.repo.db.commit()

        from app.modules.users.models import User
        bank_user = self.repo.db.query(User).filter(User.id == blood_bank_user_id).first()
        hospital_name = bank_user.blood_bank_profile.hospital_name if bank_user and bank_user.blood_bank_profile else "Blood Bank"

        if self.notif and req.patient:
            self.notif.send_to_user(
                req.patient.user_id,
                "🏥 Blood Bank Accepted Request",
                f"{hospital_name} has accepted your blood request and will coordinate collection/dispatch!",
            )
            self.notif.send_to_user(
                blood_bank_user_id,
                "🏥 Request Accepted Successfully",
                "You have accepted the patient's blood request. Please prepare the dispatch/collection.",
            )

        return req
