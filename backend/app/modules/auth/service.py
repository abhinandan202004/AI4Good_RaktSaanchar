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
        if data.phone and self.db.query(User).filter(User.phone == data.phone).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "Phone already registered")

        user = User(
            email=data.email,
            phone=data.phone,
            full_name=data.full_name,
            role=data.role,
            hashed_password=hash_password(data.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    # ── Login ─────────────────────────────────────────────────────────────────

    def login(self, data: LoginRequest) -> TokenResponse:
        user = self.db.query(User).filter(User.email == data.email).first()
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")

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
