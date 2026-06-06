from typing import Optional
from sqlalchemy.orm import Session
from app.modules.users.models import User, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def list_all(self, skip: int = 0, limit: int = 50) -> tuple[list[User], int]:
        q = self.db.query(User)
        return q.offset(skip).limit(limit).all(), q.count()

    def update(self, user: User, **kwargs) -> User:
        for k, v in kwargs.items():
            if v is not None:
                setattr(user, k, v)
        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate(self, user: User) -> User:
        user.is_active = False
        self.db.commit()
        self.db.refresh(user)
        return user
