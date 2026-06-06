from typing import Optional
from sqlalchemy.orm import Session
from app.modules.chat.models import ChatRoom, ChatMessage


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_room(self, room_id: int) -> Optional[ChatRoom]:
        return self.db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    def get_room_by_request(self, request_id: int) -> Optional[ChatRoom]:
        return self.db.query(ChatRoom).filter(ChatRoom.request_id == request_id).first()

    def create_room(self, request_id: int, donor_id: int, patient_id: int) -> ChatRoom:
        room = ChatRoom(request_id=request_id, donor_id=donor_id, patient_id=patient_id)
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def get_rooms_for_user(self, donor_id: int = None, patient_id: int = None) -> list[ChatRoom]:
        from sqlalchemy import or_
        q = self.db.query(ChatRoom)
        conditions = []
        if donor_id:
            conditions.append(ChatRoom.donor_id == donor_id)
        if patient_id:
            conditions.append(ChatRoom.patient_id == patient_id)
        
        if conditions:
            q = q.filter(or_(*conditions))
        else:
            return []
        return q.all()

    def get_messages(self, room_id: int, skip: int = 0, limit: int = 50) -> list[ChatMessage]:
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.room_id == room_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def save_message(self, room_id: int, sender_id: int, content: str, **kwargs) -> ChatMessage:
        msg = ChatMessage(room_id=room_id, sender_id=sender_id, content=content, **kwargs)
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg
