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
import random
from app.core.sns_service import SnsService
from app.modules.users.models import User
from app.modules.auth.schemas import RegisterRequest, LoginRequest, TokenResponse


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
        
        # Normalize phone: empty string or whitespace is None
        phone_val = data.phone.strip() if (data.phone and data.phone.strip()) else None
        if phone_val and self.db.query(User).filter(User.phone == phone_val).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "Phone already registered")

        from app.modules.users.models import UserRole
        if data.role == UserRole.patient:
            if not data.blood_group:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Blood group is required for registering as a patient")

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

        # Automatically seed a Patient or Donor profile if registering with a blood group
        if user.role == UserRole.patient:
            from app.modules.patients.models import Patient
            patient = Patient(
                user_id=user.id,
                blood_group_required=data.blood_group,
            )
            self.db.add(patient)
            self.db.commit()
            self.db.refresh(user)
        elif user.role == UserRole.donor and data.blood_group:
            from app.modules.donors.models import Donor, BloodGroup as DonorBloodGroup
            donor = Donor(
                user_id=user.id,
                blood_group=DonorBloodGroup(data.blood_group.value),
            )
            self.db.add(donor)
            self.db.commit()
            self.db.refresh(user)

        # Generate and store verification OTP in Redis
        is_test_account = user.email.endswith("@test.com")
        verify_code = "123456" if is_test_account else f"{random.randint(100000, 999999)}"
        self.redis.setex(f"verify:{user.email}", 600, verify_code)

        subject = "RaktaSanchaar Verification Code"
        email_body = f"Hello {user.full_name},\n\nYour RaktaSanchaar verification code is: {verify_code}\n\nThis code will expire in 10 minutes."

        # Proactively trigger AWS SES / SNS Sandbox verification for testing
        is_mock = (
            settings.AWS_ACCESS_KEY_ID in ("", "mock", "test")
            or settings.AWS_SECRET_ACCESS_KEY in ("", "mock", "test")
            or is_test_account
            or (phone_val and (phone_val.startswith("+111") or phone_val.startswith("+222") or phone_val.startswith("+333") or phone_val.startswith("+444")))
        )
        if settings.AWS_SNS_ENABLED and not is_mock:
            # Register Email in SES Sandbox
            try:
                import boto3
                ses_client = boto3.client(
                    "ses",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION
                )
                ses_client.verify_email_identity(EmailAddress=user.email)
            except Exception as ses_v_err:
                import logging
                logging.getLogger(__name__).warning(f"Failed to auto-register SES email {user.email}: {ses_v_err}")

            # Register Phone in SNS Sandbox
            if phone_val:
                try:
                    import boto3
                    sns_client = boto3.client(
                        "sns",
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                        region_name=settings.AWS_REGION
                    )
                    sns_client.create_sms_sandbox_phone_number(PhoneNumber=phone_val)
                except Exception as sns_v_err:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to auto-register SNS phone {phone_val}: {sns_v_err}")

        # Send OTP code via email only (no SMS)
        SnsService.send_sns_notification(
            email=user.email,
            subject=subject,
            message=email_body,
            email_body=email_body
        )

        return user

    # ── Verify ────────────────────────────────────────────────────────────────

    def verify(self, email: str, code: str) -> dict:
        stored = self.redis.get(f"verify:{email}")
        if not stored or stored != code:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification code")

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
        if not user.is_verified:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is not verified. Please verify your email/phone first.")

        access_token = create_access_token(user.id, user.role.value)
        refresh_token = create_refresh_token(user.id)

        # Store refresh token hash in Redis with TTL
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        self.redis.setex(f"{_REFRESH_KEY_PREFIX}{user.id}", ttl, refresh_token)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

        user_id = int(payload["sub"])

        # Verify token matches what's stored in Redis
        stored = self.redis.get(f"{_REFRESH_KEY_PREFIX}{user_id}")
        if not stored or stored != refresh_token:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired or revoked")

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

        subject = "RaktaSanchaar Verification Code"
        email_body = f"Hello {user.full_name},\n\nYour RaktaSanchaar verification code is: {verify_code}\n\nThis code will expire in 10 minutes."

        # Send OTP code via email only
        SnsService.send_sns_notification(
            email=user.email,
            subject=subject,
            message=email_body,
            email_body=email_body
        )

        return {"message": "Verification code resent successfully"}
