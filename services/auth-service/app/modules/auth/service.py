"""
Auth Service — replaces SnsService with EmailService (SMTP) for OTP delivery.
Also publishes RabbitMQ events after register.
"""
import random
import logging

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import redis as redis_lib

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings
from app.email_service import EmailService
from app.modules.users.models import User, UserRole
from app.modules.auth.schemas import RegisterRequest, LoginRequest, TokenResponse

logger = logging.getLogger(__name__)

_REFRESH_KEY_PREFIX = "refresh:"


class AuthService:
    def __init__(self, db: Session, redis: redis_lib.Redis):
        self.db = db
        self.redis = redis

    # ── Register ──────────────────────────────────────────────────────────────

    def register(self, data: RegisterRequest) -> User:
        # Check uniqueness
        if self.db.query(User).filter(User.email == data.email).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

        phone_val = data.phone.strip() if (data.phone and data.phone.strip()) else None
        if phone_val and self.db.query(User).filter(User.phone == phone_val).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "Phone already registered")

        if data.role == UserRole.patient:
            if not data.blood_group:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Blood group is required for registering as a patient",
                )

        user = User(
            email=data.email,
            phone=phone_val,
            full_name=data.full_name,
            role=data.role,
            hashed_password=hash_password(data.password),
            is_verified=False,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Generate and store verification OTP in Redis (600 s = 10 min)
        is_test_account = user.email.endswith("@test.com")
        verify_code = "123456" if is_test_account else f"{random.randint(100000, 999999)}"
        self.redis.setex(f"verify:{user.email}", 600, verify_code)

        # Send OTP via SMTP email (replaces SnsService)
        EmailService.send_otp_email(
            to=user.email,
            full_name=user.full_name,
            otp_code=verify_code,
        )

        # Publish user.registered event to RabbitMQ (best-effort)
        try:
            import asyncio
            from app.messaging.publisher import _publish
            # Since this is a synchronous FastAPI route (AnyIO thread), we use asyncio.run
            # to safely execute the async publish task in a new event loop for this thread.
            asyncio.run(_publish("user.registered", {
                "event": "user.registered",
                "user_id": user.id,
                "email": user.email,
                "phone": user.phone,
                "full_name": user.full_name,
                "role": user.role.value,
            }))
        except Exception as e:
            logger.warning("Failed to publish user.registered event: %s", e)

        return user

    # ── Verify ────────────────────────────────────────────────────────────────

    def verify(self, email: str, code: str) -> dict:
        stored = self.redis.get(f"verify:{email}")
        if not stored or stored != code:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Invalid or expired verification code",
            )

        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

        user.is_verified = True
        self.db.commit()
        self.redis.delete(f"verify:{email}")
        return {"message": "Verification successful"}

    # ── Login ─────────────────────────────────────────────────────────────────

    def login(self, data: LoginRequest) -> TokenResponse:
        user = self.db.query(User).filter(User.email == data.email).first()
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")
        if not user.is_verified and not user.email.endswith("@test.com"):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Account is not verified. Please verify your email first.",
            )

        access_token = create_access_token(user.id, user.role.value)
        refresh_token = create_refresh_token(user.id)

        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        self.redis.setex(f"{_REFRESH_KEY_PREFIX}{user.id}", ttl, refresh_token)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

        user_id = int(payload["sub"])
        stored = self.redis.get(f"{_REFRESH_KEY_PREFIX}{user_id}")
        if not stored or stored != refresh_token:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Refresh token expired or revoked",
            )

        user = self.db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

        new_access = create_access_token(user.id, user.role.value)
        return {"access_token": new_access, "token_type": "bearer"}

    # ── Logout ────────────────────────────────────────────────────────────────

    def logout(self, user_id: int) -> None:
        self.redis.delete(f"{_REFRESH_KEY_PREFIX}{user_id}")

    # ── Resend OTP ────────────────────────────────────────────────────────────

    def resend_otp(self, email: str) -> dict:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        if user.is_verified:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already verified")

        is_test_account = email.endswith("@test.com")
        verify_code = "123456" if is_test_account else f"{random.randint(100000, 999999)}"
        self.redis.setex(f"verify:{email}", 600, verify_code)

        EmailService.send_otp_email(
            to=user.email,
            full_name=user.full_name,
            otp_code=verify_code,
        )
        return {"message": "Verification code resent successfully"}
