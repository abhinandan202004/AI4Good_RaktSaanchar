"""
Unified Notifier — notification-service
Routes notifications to email and/or push based on what is available.
Replaces the old SnsService.send_sns_notification() signature.
"""
from typing import Optional

from app.email_service import EmailService
from app.push_service import PushService


class Notifier:
    @staticmethod
    def send(
        user_id: Optional[int] = None,
        email: Optional[str] = None,
        subject: str = "",
        email_body: str = "",
        push_title: str = "",
        push_message: str = "",
        priority: str = "default",
    ) -> None:
        """
        Unified notification send — email and push.
        Both channels are optional; pass None to skip that channel.
        """
        if email and email_body:
            EmailService.send_email(to=email, subject=subject, body=email_body)
        if user_id and push_title:
            PushService.send_push(
                user_id=user_id,
                title=push_title,
                message=push_message or push_title,
                priority=priority,
            )

    @staticmethod
    def send_urgent(
        user_id: Optional[int] = None,
        email: Optional[str] = None,
        subject: str = "",
        email_body: str = "",
        push_title: str = "",
        push_message: str = "",
    ) -> None:
        Notifier.send(
            user_id=user_id,
            email=email,
            subject=subject,
            email_body=email_body,
            push_title=push_title,
            push_message=push_message,
            priority="urgent",
        )
