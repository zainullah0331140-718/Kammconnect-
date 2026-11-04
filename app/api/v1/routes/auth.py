from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import login_limiter, password_reset_limiter
from app.core.security import generate_csrf_token
from app.db.session import get_db
from app.dependencies.auth import CurrentUser, get_client_ip
from app.repositories.users import UserRepository
from app.schemas.auth import (
    CsrfResponse,
    CustomerRegister,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    ProviderRegister,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserPublic
from app.services.auth_service import AuthService
from app.services.serializers import user_public

router = APIRouter(prefix="/auth", tags=["Authentication"])


def set_auth_cookies(response: Response, tokens: dict) -> None:
    secure = settings.cookie_secure
    response.set_cookie(
        key=settings.access_cookie_name,
        value=tokens["access_token"],
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=tokens["refresh_token"],
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/v1/auth",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=tokens["csrf_token"],
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    secure = settings.cookie_secure
    response.delete_cookie(
        settings.access_cookie_name, path="/", secure=secure, samesite="lax"
    )
    response.delete_cookie(
        settings.refresh_cookie_name,
        path="/api/v1/auth",
        secure=secure,
        samesite="lax",
    )
    response.delete_cookie(
        settings.csrf_cookie_name, path="/", secure=secure, samesite="lax"
    )


@router.post(
    "/register/customer", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def register_customer(
    data: CustomerRegister,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    service = AuthService(db)
    _user, tokens = service.register_customer(data)
    db.commit()
    set_auth_cookies(response, tokens)
    return tokens


@router.post(
    "/register/provider", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def register_provider(
    data: ProviderRegister,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    service = AuthService(db)
    _user, tokens = service.register_provider(data)
    db.commit()
    set_auth_cookies(response, tokens)
    return tokens


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    ip = get_client_ip(request) or "unknown"
    key = f"login:{ip}:{str(data.email).lower()}"
    retry_after = login_limiter.check(
        key, settings.login_max_attempts, settings.login_window_seconds
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    service = AuthService(db)
    try:
        _user, tokens = service.login(
            str(data.email), data.password, ip_address=get_client_ip(request)
        )
    except HTTPException:
        login_limiter.record_failure(
            key, settings.login_max_attempts, settings.login_window_seconds
        )
        db.rollback()
        raise
    login_limiter.reset(key, settings.login_max_attempts, settings.login_window_seconds)
    db.commit()
    set_auth_cookies(response, tokens)
    return tokens


@router.post("/password-reset/request", response_model=PasswordResetResponse)
def request_password_reset(
    data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    ip = get_client_ip(request) or "unknown"
    key = f"password-reset:{ip}"
    retry_after = password_reset_limiter.check(
        key,
        settings.password_reset_max_attempts,
        settings.password_reset_window_seconds,
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    password_reset_limiter.record_failure(
        key,
        settings.password_reset_max_attempts,
        settings.password_reset_window_seconds,
    )
    payload = AuthService(db).request_password_reset(
        str(data.email), ip_address=get_client_ip(request)
    )
    db.commit()
    return payload


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(
    data: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    service = AuthService(db)
    service.reset_password(
        token=data.token,
        new_password=data.new_password,
        ip_address=get_client_ip(request),
    )
    db.commit()
    return {
        "message": "Your password has been reset. Log in with your new password."
    }


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    data: PasswordChangeRequest,
    request: Request,
    response: Response,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> dict:
    service = AuthService(db)
    user = service.change_password(
        user=user,
        current_password=data.current_password,
        new_password=data.new_password,
        ip_address=get_client_ip(request),
    )
    tokens = service.issue_tokens(user)
    db.commit()
    set_auth_cookies(response, tokens)
    return tokens


@router.get("/csrf", response_model=CsrfResponse)
def get_csrf_token(response: Response) -> dict:
    token = generate_csrf_token()
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"csrf_token": token}


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(
    request: Request,
    response: Response,
    data: RefreshRequest | None = None,
    db: Session = Depends(get_db),
) -> dict:
    token = None
    if data is not None:
        token = data.refresh_token
    token = token or request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )
    service = AuthService(db)
    _user, tokens = service.refresh(token)
    db.commit()
    set_auth_cookies(response, tokens)
    return tokens


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    data: RefreshRequest | None = None,
    db: Session = Depends(get_db),
) -> dict:
    token = data.refresh_token if data is not None else None
    token = token or request.cookies.get(settings.refresh_cookie_name)
    service = AuthService(db)
    service.logout(token)
    db.commit()
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserPublic)
def me(user: CurrentUser, db: Session = Depends(get_db)) -> UserPublic:
    return user_public(user)


@router.get("/me/context")
def me_context(user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    profile_status = UserRepository(db).provider_status_for_user(user.id)
    payload = user_public(user).model_dump()
    payload["provider_verification_status"] = profile_status
    return payload
