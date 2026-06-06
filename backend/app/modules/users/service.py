from fastapi import HTTPException, status
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserUpdate


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_user(self, user_id: int):
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
        return user

    def list_users(self, skip: int = 0, limit: int = 50):
        items, total = self.repo.list_all(skip, limit)
        return {"total": total, "items": items}

    def update_user(self, user_id: int, data: UserUpdate, requesting_user):
        # Users can only update themselves; admins can update anyone
        if requesting_user.role.value != "admin" and requesting_user.id != user_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot update another user's profile")
        user = self.get_user(user_id)
        return self.repo.update(user, full_name=data.full_name, phone=data.phone)

    def deactivate_user(self, user_id: int):
        user = self.get_user(user_id)
        return self.repo.deactivate(user)
