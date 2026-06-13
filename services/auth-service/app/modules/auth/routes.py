from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import redis as redis_lib

from app.core.dependencies import get_db, get_redis, get_current_user
from app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    AccessTokenResponse,
    UserOut,
    VerifyRequest,
    ResendOtpRequest,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def _svc(db: Session = Depends(get_db), r: redis_lib.Redis = Depends(get_redis)) -> AuthService:
    return AuthService(db, r)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, svc: AuthService = Depends(_svc)):
    """Register a new user (donor / patient / coordinator / blood_bank)."""
    return svc.register(data)


@router.post("/verify", status_code=status.HTTP_200_OK)
def verify(data: VerifyRequest, svc: AuthService = Depends(_svc)):
    """Verify user registration OTP code."""
    return svc.verify(data.email, data.code)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, svc: AuthService = Depends(_svc)):
    """Login and receive access + refresh tokens."""
    return svc.login(data)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(data: RefreshRequest, svc: AuthService = Depends(_svc)):
    """Get a new access token using a valid refresh token."""
    return svc.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user=Depends(get_current_user),
    svc: AuthService = Depends(_svc),
):
    """Revoke the refresh token (logout)."""
    svc.logout(current_user.id)


@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.post("/resend-otp", status_code=status.HTTP_200_OK)
def resend_otp(data: ResendOtpRequest, svc: AuthService = Depends(_svc)):
    """Resend verification OTP to user's email."""
    return svc.resend_otp(data.email)
