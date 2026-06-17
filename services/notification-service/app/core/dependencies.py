from typing import Generator

import redis as redis_lib
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.database import SessionLocal, CoreSessionLocal
from app.core.security import decode_token

security_scheme = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_core_db() -> Generator[Session, None, None]:
    db = CoreSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis() -> redis_lib.Redis:
    return redis_lib.from_url(settings.REDIS_URL, decode_responses=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    core_db: Session = Depends(get_core_db),
):
    """
    Decodes the JWT (issued by auth-service, shared SECRET_KEY).
    Looks up a lightweight user stub from the users table in core schema.
    """
    from app.modules.users.models import User  # local import to avoid circular

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    try:
        payload = decode_token(token)
        print("DEBUG PAYLOAD:", payload, flush=True)
    except Exception as e:
        print("DEBUG DECODE ERROR:", e, flush=True)
        payload = None

    if not payload or payload.get("type") != "access":
        raise credentials_exc

    user_id: int = int(payload.get("sub"))
    user = core_db.query(User).filter(User.id == user_id, User.is_active == True).first()
    print("DEBUG USER FOUND:", user, "FOR ID", user_id, flush=True)
    if not user:
        raise credentials_exc
    return user


def require_roles(*roles: str):
    def guard(current_user=Depends(get_current_user)):
        if current_user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {list(roles)}",
            )
        return current_user
    return guard


require_admin       = require_roles("admin")
require_coordinator = require_roles("admin", "coordinator")
require_blood_bank  = require_roles("admin", "blood_bank")
require_donor       = require_roles("admin", "coordinator", "donor")
require_patient     = require_roles("admin", "coordinator", "patient")
