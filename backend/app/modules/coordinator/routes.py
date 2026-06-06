from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles, get_current_user
from app.modules.coordinator.schemas import (
    DashboardStats,
    ManualAssignIn,
    EscalateIn,
    EmergencyBroadcastIn,
    RequestSummary,
)
from app.modules.coordinator.service import CoordinatorService
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="/coordinator", tags=["Coordinator"])


def _svc(db: Session = Depends(get_db)) -> CoordinatorService:
    return CoordinatorService(db, NotificationService(db))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardStats)
def dashboard(
    svc: CoordinatorService = Depends(_svc),
    _=Depends(require_roles("admin", "coordinator")),
):
    """Live operational overview — request counts, donor availability."""
    return svc.get_dashboard()


# ── Active Requests ───────────────────────────────────────────────────────────

@router.get("/requests/active", response_model=list[RequestSummary])
def active_requests(
    svc: CoordinatorService = Depends(_svc),
    _=Depends(require_roles("admin", "coordinator")),
):
    """All requests in pending / matched / accepted / escalated state."""
    return svc.get_active_requests()


# ── Manual Override ───────────────────────────────────────────────────────────

@router.patch("/requests/{request_id}/override", response_model=RequestSummary)
def override_assignment(
    request_id: int,
    data: ManualAssignIn,
    svc: CoordinatorService = Depends(_svc),
    current_user=Depends(require_roles("admin", "coordinator")),
):
    """Manually assign a specific donor to a blood request (overrides AI match)."""
    return svc.manually_assign(request_id, data, current_user.id)


# ── Escalate ──────────────────────────────────────────────────────────────────

@router.patch("/requests/{request_id}/escalate", response_model=RequestSummary)
def escalate(
    request_id: int,
    data: EscalateIn,
    svc: CoordinatorService = Depends(_svc),
    current_user=Depends(require_roles("admin", "coordinator")),
):
    """Escalate a blood request that has stalled."""
    return svc.escalate_request(request_id, data, current_user.id)


# ── Emergency Broadcast ───────────────────────────────────────────────────────

@router.post("/emergency")
def emergency_broadcast(
    data: EmergencyBroadcastIn,
    svc: CoordinatorService = Depends(_svc),
    _=Depends(require_roles("admin", "coordinator")),
):
    """Broadcast an emergency alert to available donors. Optionally filter by blood group."""
    return svc.emergency_broadcast(data)
