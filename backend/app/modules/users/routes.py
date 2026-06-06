from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user, require_roles
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService
from app.modules.users.schemas import UserOut, UserUpdate, UserListOut

router = APIRouter(prefix="/users", tags=["Users"])


def _svc(db: Session = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


@router.get("/", response_model=UserListOut)
def list_users(
    skip: int = 0,
    limit: int = 50,
    svc: UserService = Depends(_svc),
    _=Depends(require_roles("admin", "coordinator")),
):
    return svc.list_users(skip, limit)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    svc: UserService = Depends(_svc),
    _=Depends(get_current_user),
):
    return svc.get_user(user_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    svc: UserService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.update_user(user_id, data, current_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    svc: UserService = Depends(_svc),
    _=Depends(require_roles("admin")),
):
    svc.deactivate_user(user_id)
