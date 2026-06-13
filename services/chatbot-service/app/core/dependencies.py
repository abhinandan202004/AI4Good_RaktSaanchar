from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.core.config import settings

security_scheme = HTTPBearer()


class CurrentUser:
    def __init__(self, id: int, role: str, token: str):
        self.id = id
        self.role = role
        self.token = token


def get_db() -> Generator[None, None, None]:
    """Mock database generator for compatibility with existing route signature."""
    yield None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> CurrentUser:
    """Decodes JWT access token and returns user details and token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type, access token required",
            )
        user_id = int(payload["sub"])
        role = payload.get("role", "donor")
        return CurrentUser(id=user_id, role=role, token=token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
