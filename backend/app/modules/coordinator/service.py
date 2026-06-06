from fastapi import HTTPException, status

from sqlalchemy.orm import Session

from app.modules.blood_requests.models import BloodRequest, RequestStatus, AssignedBy
from app.modules.donors.models import Donor
from app.modules.notifications.service import NotificationService
from app.modules.coordinator.schemas import (
    DashboardStats,
    ManualAssignIn,
    EscalateIn,
    EmergencyBroadcastIn,
    RequestSummary,
)


class CoordinatorService:
    def __init__(self, db: Session, notif: NotificationService):
        self.db = db
        self.notif = notif

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def get_dashboard(self) -> DashboardStats:
        def count(s):
            return self.db.query(BloodRequest).filter(BloodRequest.status == s).count()

        return DashboardStats(
            total_requests=self.db.query(BloodRequest).count(),
            pending=count(RequestStatus.pending),
            matched=count(RequestStatus.matched),
            accepted=count(RequestStatus.accepted),
            fulfilled=count(RequestStatus.fulfilled),
            escalated=count(RequestStatus.escalated),
            cancelled=count(RequestStatus.cancelled),
            available_donors=self.db.query(Donor).filter(Donor.is_available == True).count(),
        )

    # ── Active Requests ───────────────────────────────────────────────────────

    def get_active_requests(self) -> list[RequestSummary]:
        active_statuses = [
            RequestStatus.pending,
            RequestStatus.matched,
            RequestStatus.accepted,
            RequestStatus.escalated,
        ]
        requests = (
            self.db.query(BloodRequest)
            .filter(BloodRequest.status.in_(active_statuses))
            .order_by(BloodRequest.updated_at.desc())
            .all()
        )
        return [RequestSummary.model_validate(r) for r in requests]

    # ── Manual Override ───────────────────────────────────────────────────────

    def manually_assign(
        self, request_id: int, data: ManualAssignIn, coordinator_user_id: int
    ) -> RequestSummary:
        request = self._get_request_or_404(request_id)

        donor = self.db.query(Donor).filter(Donor.id == data.donor_id).first()
        if not donor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Donor {data.donor_id} not found.",
            )
        if not donor.is_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Selected donor is not currently available.",
            )

        request.assigned_donor_id = data.donor_id
        request.assigned_by = AssignedBy.coordinator
        request.coordinator_note = data.note
        request.status = RequestStatus.matched
        self.db.commit()
        self.db.refresh(request)

        # Notify donor + patient
        self.notif.notify_request_matched(
            donor_user_id=donor.user_id,
            patient_user_id=request.patient.user_id,
        )

        return RequestSummary.model_validate(request)

    # ── Escalate ──────────────────────────────────────────────────────────────

    def escalate_request(
        self, request_id: int, data: EscalateIn, coordinator_user_id: int
    ) -> RequestSummary:
        request = self._get_request_or_404(request_id)
        request.status = RequestStatus.escalated
        if data.note:
            request.coordinator_note = data.note
        self.db.commit()
        self.db.refresh(request)

        self.notif.notify_request_escalated(coordinator_user_id, request_id)
        return RequestSummary.model_validate(request)

    # ── Emergency Broadcast ───────────────────────────────────────────────────

    def emergency_broadcast(self, data: EmergencyBroadcastIn) -> dict:
        if data.blood_group:
            count = self.notif.broadcast_to_donors(
                blood_group=data.blood_group,
                title="🚨 Emergency Blood Request",
                body=data.message,
            )
        else:
            count = self.notif.broadcast_to_all_donors(
                title="🚨 Emergency Blood Request",
                body=data.message,
            )
        return {"detail": f"Emergency alert sent to {count} donor(s)."}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_request_or_404(self, request_id: int) -> BloodRequest:
        req = self.db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"BloodRequest {request_id} not found.",
            )
        return req
