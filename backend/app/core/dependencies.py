from typing import Generator

import redis as redis_lib
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import decode_token

security_scheme = HTTPBearer()

# ── DB Session ────────────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Redis ─────────────────────────────────────────────────────────────────────

def get_redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
):
    """Decode JWT and return the User ORM object."""
    from app.modules.users.models import User  # local import to avoid circular

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exc

    user_id: int = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise credentials_exc
    return user


# ── Role Guards ───────────────────────────────────────────────────────────────

def require_roles(*roles: str):
    """Factory that returns a dependency enforcing role membership."""
    def guard(current_user=Depends(get_current_user)):
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {list(roles)}",
            )
        return current_user
    return guard


# Convenience shorthands
require_admin        = require_roles("admin")
require_coordinator  = require_roles("admin", "coordinator")
require_blood_bank   = require_roles("admin", "blood_bank")
require_donor        = require_roles("admin", "coordinator", "donor")
require_patient      = require_roles("admin", "coordinator", "patient")
