# Chat models — standalone, no cross-service FK to users table
# (donor_user_id / patient_user_id are logical references only)
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    # Logical FK to core.blood_requests — stored as plain int (no enforced constraint)
    request_id = Column(Integer, unique=True, nullable=False, index=True)
    donor_user_id = Column(Integer, nullable=False)
    patient_user_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    messages = relationship("ChatMessage", back_populates="room", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    sender_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    is_translated = Column(Boolean, default=False)
    original_lang = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    room = relationship("ChatRoom", back_populates="messages")
