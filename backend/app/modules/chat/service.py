"""
ChatService
-----------
Handles chat room lifecycle. Rooms are automatically created when a donor
accepts a blood request (idempotent — one room per request).
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.chat.models import ChatRoom
from app.modules.chat.repository import ChatRepository
from app.modules.donors.repository import DonorRepository
from app.modules.patients.repository import PatientRepository
from app.modules.blood_requests.repository import BloodRequestRepository


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ChatRepository(db)

    def get_or_create_room(self, request_id: int) -> Optional[ChatRoom]:
        """
        Idempotent room creation.
        Called automatically when a donor accepts a blood request.
        Returns the existing room or creates a new one.
        """
        # Check if room already exists
        existing = self.repo.get_room_by_request(request_id)
        if existing:
            return existing

        # Load the blood request to get donor + patient ids
        blood_request = BloodRequestRepository(self.db).get_by_id(request_id)
        if not blood_request or not blood_request.assigned_donor_id:
            return None

        donor_id = blood_request.assigned_donor_id
        patient_id = blood_request.patient_id

        return self.repo.create_room(
            request_id=request_id,
            donor_id=donor_id,
            patient_id=patient_id,
        )

    def get_room(self, room_id: int) -> Optional[ChatRoom]:
        return self.repo.get_room(room_id)

    def get_rooms_for_user(self, user_id: int, db: Session) -> list[ChatRoom]:
        donor = DonorRepository(db).get_by_user_id(user_id)
        patient = PatientRepository(db).get_by_user_id(user_id)
        return self.repo.get_rooms_for_user(
            donor_id=donor.id if donor else None,
            patient_id=patient.id if patient else None,
        )
