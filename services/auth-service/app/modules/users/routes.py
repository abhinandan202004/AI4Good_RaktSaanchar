from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.dependencies import get_db, get_current_user, require_roles
from app.modules.users.models import User
from app.modules.auth.schemas import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserOut])
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "coordinator")),
):
    """List all users (admin/coordinator only)."""
    return db.query(User).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Get a user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update user profile (self or admin)."""
    if current_user.id != user_id and current_user.role.value != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot modify another user's profile")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone.strip() or None

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    """Deactivate a user account (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.is_active = False
    db.commit()
