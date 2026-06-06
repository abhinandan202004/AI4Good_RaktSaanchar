from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MessageOut(BaseModel):
    id: int
    room_id: int
    sender_id: int
    content: str
    is_translated: bool
    original_lang: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRoomOut(BaseModel):
    id: int
    request_id: int
    donor_id: int
    patient_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessage(BaseModel):
    content: str
