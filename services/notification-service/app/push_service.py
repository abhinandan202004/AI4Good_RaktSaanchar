"""
Push Notification Service — notification-service
Uses ntfy.sh (free, open-source) as SMS/push replacement for AWS SNS.

Each user subscribes to a personal topic: raktsaanchar-{user_id}
Frontend uses SSE or ntfy.js to receive push events.
"""
import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class PushService:
    NTFY_BASE_URL = settings.NTFY_BASE_URL
    NTFY_TOPIC_PREFIX = settings.NTFY_TOPIC_PREFIX

    @classmethod
    def _topic(cls, user_id: int) -> str:
        return f"{cls.NTFY_TOPIC_PREFIX}-{user_id}"

    @classmethod
    def send_push(
        cls,
        user_id: int,
        title: str,
        message: str,
        priority: str = "default",
        tags: str = "drop_of_blood",
    ) -> bool:
        """
        Send a push notification via ntfy.sh.
        Priority: "urgent" | "high" | "default" | "low" | "min"
        """
        topic = cls._topic(user_id)
        try:
            response = httpx.post(
                f"{cls.NTFY_BASE_URL}/{topic}",
                content=message,
                headers={
                    "Title": title,
                    "Priority": priority,
                    "Tags": tags,
                },
                timeout=5.0,
            )
            success = response.status_code == 200
            if not success:
                logger.warning("ntfy push failed (user=%s, status=%s)", user_id, response.status_code)
            return success
        except Exception as exc:
            logger.warning("Push send failed (user=%s): %s", user_id, exc)
            return False

    @classmethod
    def send_urgent(cls, user_id: int, title: str, message: str) -> bool:
        return cls.send_push(user_id, title, message, priority="urgent")

    @classmethod
    def send_high(cls, user_id: int, title: str, message: str) -> bool:
        return cls.send_push(user_id, title, message, priority="high")
