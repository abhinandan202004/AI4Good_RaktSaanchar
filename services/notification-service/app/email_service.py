"""
Email Service — notification-service
Replaces AWS SES entirely. Uses SMTP (Gmail / Brevo / any SMTP relay).
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    SMTP_HOST = settings.SMTP_HOST
    SMTP_PORT = settings.SMTP_PORT
    SMTP_USER = settings.SMTP_USER
    SMTP_PASS = settings.SMTP_PASS
    SENDER_NAME = settings.SENDER_NAME

    @classmethod
    def send_email(cls, to: str, subject: str, body: str) -> bool:
        if not cls.SMTP_USER or not cls.SMTP_PASS:
            logger.warning("SMTP not configured — email skipped (to=%s)", to)
            return False
        try:
            msg = MIMEMultipart()
            msg["From"] = f"{cls.SENDER_NAME} <{cls.SMTP_USER}>"
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))
            with smtplib.SMTP(cls.SMTP_HOST, cls.SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(cls.SMTP_USER, cls.SMTP_PASS)
                server.sendmail(cls.SMTP_USER, [to], msg.as_string())
            logger.info("✉️  Email sent to %s", to)
            return True
        except Exception as exc:
            logger.warning("Email send failed (to=%s): %s", to, exc)
            return False
