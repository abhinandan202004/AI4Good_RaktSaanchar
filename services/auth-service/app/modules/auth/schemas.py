from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.modules.users.models import UserRole


# Blood group enum (duplicated here to avoid cross-service imports)
import enum


class BloodGroup(str, enum.Enum):
    O_POS = "O+"
    O_NEG = "O-"
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"


# ── Register ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    password: str
    full_name: str
    role: UserRole = UserRole.donor
    blood_group: Optional[BloodGroup] = None


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Refresh ───────────────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Current User ──────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    email: str
    phone: Optional[str]
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Verify Request ────────────────────────────────────────────────────────────

class VerifyRequest(BaseModel):
    email: EmailStr
    code: str


# ── Resend OTP Request ────────────────────────────────────────────────────────

class ResendOtpRequest(BaseModel):
    email: EmailStr


# ── User update ───────────────────────────────────────────────────────────────

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


# ── Password Reset ────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

