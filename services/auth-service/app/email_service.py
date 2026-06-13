"""
Email Service — replaces AWS SES entirely.
Uses SMTP (Gmail / Brevo / any SMTP relay) — 100% free.

Gmail setup:
  1. Enable 2FA on Gmail account
  2. Go to: Google Account → Security → App Passwords
  3. Generate 16-char App Password
  4. Set SMTP_USER=your@gmail.com  SMTP_PASS=<16-char password>
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
        """
        Send a plain-text email via SMTP.
        Returns True on success, False on failure (never raises).
        """
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

            logger.info("✉️  Email sent to %s (subject: %s)", to, subject)
            return True

        except Exception as exc:
            logger.warning("Email send failed (to=%s): %s", to, exc)
            return False

    @classmethod
    def send_otp_email(cls, to: str, full_name: str, otp_code: str) -> bool:
        subject = "RaktSaanchar — Your Verification Code"
        body = (
            f"Hello {full_name},\n\n"
            f"Your RaktSaanchar verification code is:\n\n"
            f"    {otp_code}\n\n"
            f"This code expires in 10 minutes.\n\n"
            f"If you did not create an account, please ignore this email.\n\n"
            f"Best regards,\n"
            f"The RaktSaanchar Team"
        )
        return cls.send_email(to, subject, body)
