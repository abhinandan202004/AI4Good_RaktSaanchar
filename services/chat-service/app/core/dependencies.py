from typing import Generator

from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import SessionLocal

security_scheme = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def decode_token(token: str):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> int:
    """Returns user_id from JWT. Chat-service doesn't need a DB User lookup."""
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return int(payload["sub"])
