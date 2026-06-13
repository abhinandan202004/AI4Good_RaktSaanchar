from typing import Optional
from sqlalchemy.orm import Session
from app.modules.blood_requests.models import BloodRequest, RequestStatus


class BloodRequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> BloodRequest:
        req = BloodRequest(**kwargs)
        self.db.add(req)
        self.db.commit()
        self.db.refresh(req)
        return req

    def get_by_id(self, req_id: int) -> Optional[BloodRequest]:
        return self.db.query(BloodRequest).filter(BloodRequest.id == req_id).first()

    def list_all(self, skip: int = 0, limit: int = 50) -> tuple[list[BloodRequest], int]:
        q = self.db.query(BloodRequest).order_by(BloodRequest.id.desc())
        return q.offset(skip).limit(limit).all(), q.count()

    def list_by_patient(self, patient_id: int) -> list[BloodRequest]:
        return self.db.query(BloodRequest).filter(BloodRequest.patient_id == patient_id).all()

    def list_active(self) -> list[BloodRequest]:
        active = [RequestStatus.pending, RequestStatus.matched, RequestStatus.accepted, RequestStatus.escalated]
        return self.db.query(BloodRequest).filter(BloodRequest.status.in_(active)).all()

    def update_status(self, req: BloodRequest, status: RequestStatus, **extras) -> BloodRequest:
        req.status = status
        for k, v in extras.items():
            setattr(req, k, v)
        self.db.commit()
        self.db.refresh(req)
        return req
