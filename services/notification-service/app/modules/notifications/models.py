from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.core.database import Base


class NotificationType(str, enum.Enum):
    request = "request"
    alert = "alert"
    badge = "badge"
    system = "system"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    type = Column(Enum(NotificationType), default=NotificationType.system)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="notifications")
