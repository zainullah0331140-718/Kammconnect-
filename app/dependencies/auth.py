from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import TokenError, decode_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.provider import ProviderProfile
from app.models.user import User
from app.repositories.providers import ProviderRepository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=False
)

DbSession = Annotated[Session, Depends(get_db)]


def get_client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


def _unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _user_from_token(db: Session, token: str) -> User:
    try:
        payload = decode_token(token, "access")
        user_id = int(payload["sub"])
    except (TokenError, TypeError, ValueError):
        raise _unauthorized("Invalid or expired session")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired session")
    return user


async def get_current_user(
    request: Request,
    db: DbSession,
    bearer_token: str | None = Depends(oauth2_scheme),
) -> User:
    token = bearer_token or request.cookies.get(settings.access_cookie_name)
    if not token:
        raise _unauthorized()
    user = _user_from_token(db, token)
    request.state.user = user
    return user


async def get_optional_user(
    request: Request,
    db: DbSession,
    bearer_token: str | None = Depends(oauth2_scheme),
) -> User | None:
    token = bearer_token or request.cookies.get(settings.access_cookie_name)
    if not token:
        return None
    try:
        user = _user_from_token(db, token)
    except HTTPException:
        return None
    request.state.user = user
    return user


def require_roles(*roles: str):
    allowed = set(roles)

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return dependency


require_customer = require_roles(UserRole.CUSTOMER.value)
require_provider = require_roles(UserRole.PROVIDER.value)
require_admin = require_roles(UserRole.ADMIN.value)


class Pagination:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=settings.max_page_size),
    ) -> None:
        self.page = page
        self.page_size = page_size


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
PaginationParams = Annotated[Pagination, Depends(Pagination)]


def get_provider_profile(
    user: User = Depends(require_provider), db: Session = Depends(get_db)
) -> ProviderProfile:
    profile = ProviderRepository(db).get_by_user_id(user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Create your provider profile first",
        )
    return profile


