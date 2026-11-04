from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.models.provider import ProviderProfile
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(func.lower(User.email) == email.lower()))

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str,
        phone: str | None,
        role: str,
    ) -> User:
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            full_name=full_name,
            phone=phone,
            role=role,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def list(
        self,
        *,
        role: str | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        stmt = (
            select(User)
            .options(selectinload(User.provider_profile))
            .order_by(User.created_at.desc())
        )
        if role:
            stmt = stmt.where(User.role == role)
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        users = list(
            self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        )
        return users, total

    def count_by_role(self, role: str) -> int:
        return (
            self.db.scalar(select(func.count(User.id)).where(User.role == role)) or 0
        )

    def count_all(self) -> int:
        return self.db.scalar(select(func.count(User.id))) or 0

    def count_active_admins(self) -> int:
        return (
            self.db.scalar(
                select(func.count(User.id)).where(
                    User.role == UserRole.ADMIN.value, User.is_active.is_(True)
                )
            )
            or 0
        )

    def login_stats(
        self, user_ids: list[int]
    ) -> dict[int, tuple[datetime | None, int]]:
        if not user_ids:
            return {}
        rows = self.db.execute(
            select(
                AuditLog.actor_user_id,
                func.max(AuditLog.created_at),
                func.count(AuditLog.id),
            )
            .where(
                AuditLog.action == "auth.login",
                AuditLog.actor_user_id.in_(user_ids),
            )
            .group_by(AuditLog.actor_user_id)
        ).all()
        return {row[0]: (row[1], row[2]) for row in rows}

    def provider_status_for_user(self, user_id: int) -> str | None:
        return self.db.scalar(
            select(ProviderProfile.verification_status).where(
                ProviderProfile.user_id == user_id
            )
        )
