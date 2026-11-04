from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.audit import AuditRepository
from app.repositories.users import UserRepository


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)

    def delete_account(
        self, *, user: User, password: str, ip_address: str | None = None
    ) -> list[str]:
        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is incorrect",
            )
        if (
            user.role == UserRole.ADMIN.value
            and user.is_active
            and self.users.count_active_admins() <= 1
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one active administrator must remain",
            )

        profile = user.provider_profile
        image_paths: list[str] = []
        if user.profile_image:
            image_paths.append(user.profile_image)
        if profile is not None:
            if profile.profile_image:
                image_paths.append(profile.profile_image)
            for work_image in profile.work_images:
                if work_image.image_path:
                    image_paths.append(work_image.image_path)
            for advertisement in profile.advertisements:
                if advertisement.image_path:
                    image_paths.append(advertisement.image_path)

        self.audit.add(
            actor_user_id=None,
            action="user.delete_self",
            entity_type="user",
            entity_id=user.id,
            details={
                "email": user.email,
                "role": user.role,
                "provider_id": profile.id if profile else None,
            },
            ip_address=ip_address,
        )
        self.db.delete(user)
        self.db.flush()
        return image_paths
