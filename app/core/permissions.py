from collections.abc import Iterable

from app.models.enums import UserRole
from app.models.user import User


class PermissionDenied(Exception):
    pass


def user_has_role(user: User, roles: Iterable[str]) -> bool:
    return user.role in set(roles)


def has_role(user: User, *roles: UserRole | str) -> bool:
    allowed = {role.value if isinstance(role, UserRole) else role for role in roles}
    return user.role in allowed


def ensure_self_or_admin(user: User, owner_id: int) -> None:
    if user.id != owner_id and not user.is_admin:
        raise PermissionDenied("You do not have permission to perform this action")
