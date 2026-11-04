from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_password_reset_email
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_csrf_token,
    generate_password_reset_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.models.enums import UserRole
from app.models.mixins import utcnow as naive_utcnow
from app.models.user import User
from app.repositories.audit import AuditRepository
from app.repositories.password_reset_tokens import PasswordResetTokenRepository
from app.repositories.providers import ProviderRepository
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.users import UserRepository
from app.schemas.auth import CustomerRegister, ProviderRegister
from app.services.serializers import user_public

INVALID_CREDENTIALS = "Invalid email or password"
PASSWORD_RESET_MESSAGE = (
    "If an account exists for that email, a password reset link has been sent."
)
INVALID_RESET_TOKEN = "This password reset link is invalid or has expired."


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.providers = ProviderRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)
        self.password_reset_tokens = PasswordResetTokenRepository(db)
        self.audit = AuditRepository(db)

    def register_customer(self, data: CustomerRegister) -> tuple[User, dict]:
        if self.users.get_by_email(str(data.email)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )
        user = self.users.create(
            email=str(data.email),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            role=UserRole.CUSTOMER.value,
        )
        return user, self.issue_tokens(user)

    def register_provider(self, data: ProviderRegister) -> tuple[User, dict]:
        if self.users.get_by_email(str(data.email)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )
        user = self.users.create(
            email=str(data.email),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            role=UserRole.PROVIDER.value,
        )
        self.providers.create(
            user_id=user.id,
            business_name=data.business_name,
            description=data.description,
            experience_years=data.experience_years,
            city=data.city,
            area=data.area,
            address=data.address,
            contact_phone=data.contact_phone or data.phone,
            whatsapp_number=data.whatsapp_number or data.contact_phone or data.phone,
        )
        return user, self.issue_tokens(user)

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=INVALID_CREDENTIALS,
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=INVALID_CREDENTIALS,
                headers={"WWW-Authenticate": "Bearer"},
            )
        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        return user

    def login(
        self, email: str, password: str, ip_address: str | None = None
    ) -> tuple[User, dict]:
        user = self.authenticate(email, password)
        tokens = self.issue_tokens(user)
        self.audit.add(
            actor_user_id=user.id,
            action="auth.login",
            entity_type="user",
            entity_id=user.id,
            details={"email": user.email, "role": user.role},
            ip_address=ip_address,
        )
        return user, tokens

    def issue_tokens(self, user: User) -> dict:
        access_token, _ = create_access_token(user.id, user.role)
        refresh_token, refresh_expires = create_refresh_token(user.id)
        self.refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=refresh_expires,
        )
        csrf_token = generate_csrf_token()
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "csrf_token": csrf_token,
            "user": user_public(user),
        }

    def refresh(self, refresh_token: str) -> tuple[User, dict]:
        try:
            payload = decode_token(refresh_token, "refresh")
        except TokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please log in again.",
            ) from exc

        record = self.refresh_tokens.get_by_hash(hash_token(refresh_token))
        if (
            record is None
            or record.revoked_at is not None
            or record.expires_at < naive_utcnow()
            or str(record.user_id) != str(payload.get("sub"))
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please log in again.",
            )

        user = self.users.get(record.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please log in again.",
            )

        self.refresh_tokens.revoke(record)
        return user, self.issue_tokens(user)

    def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        record = self.refresh_tokens.get_by_hash(hash_token(refresh_token))
        if record is not None and record.revoked_at is None:
            self.refresh_tokens.revoke(record)

    def _issue_password_reset(
        self,
        *,
        user: User,
        actor_user_id: int,
        action: str,
        ip_address: str | None,
    ) -> tuple[str, str, bool]:
        token = generate_password_reset_token()
        expires_at = naive_utcnow() + timedelta(
            minutes=settings.password_reset_expire_minutes
        )
        self.password_reset_tokens.invalidate_for_user(user.id)
        self.password_reset_tokens.create(
            user_id=user.id, token_hash=hash_token(token), expires_at=expires_at
        )
        reset_url = (
            f"{settings.password_reset_origin}/reset-password?token={token}"
        )
        sent = send_password_reset_email(
            to_email=user.email, full_name=user.full_name, reset_url=reset_url
        )
        self.audit.add(
            actor_user_id=actor_user_id,
            action=action,
            entity_type="user",
            entity_id=user.id,
            details={"email": user.email, "role": user.role},
            ip_address=ip_address,
        )
        self.db.flush()
        return token, reset_url, sent

    def request_password_reset(
        self, email: str, ip_address: str | None = None
    ) -> dict:
        user = self.users.get_by_email(email)
        if user is None or not user.is_active:
            return {"message": PASSWORD_RESET_MESSAGE}
        token, reset_url, _sent = self._issue_password_reset(
            user=user,
            actor_user_id=user.id,
            action="auth.password_reset_requested",
            ip_address=ip_address,
        )
        payload: dict = {"message": PASSWORD_RESET_MESSAGE}
        if settings.expose_password_reset_link:
            payload["reset_token"] = token
            payload["reset_url"] = reset_url
        return payload

    def admin_password_reset(
        self,
        *,
        target: User,
        admin: User,
        ip_address: str | None = None,
    ) -> dict:
        if not target.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Activate this account before sending a password reset link.",
            )
        token, reset_url, sent = self._issue_password_reset(
            user=target,
            actor_user_id=admin.id,
            action="admin.password_reset",
            ip_address=ip_address,
        )
        payload: dict = {
            "message": (
                "Password reset link generated and emailed to the user."
                if sent
                else "Password reset link generated."
            ),
            "email_sent": sent,
        }
        if settings.expose_password_reset_link:
            payload["reset_token"] = token
            payload["reset_url"] = reset_url
        return payload

    def reset_password(
        self,
        *,
        token: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> User:
        record = self.password_reset_tokens.get_by_hash(hash_token(token))
        if (
            record is None
            or record.used_at is not None
            or record.expires_at < naive_utcnow()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_RESET_TOKEN,
            )
        user = self.users.get(record.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_RESET_TOKEN,
            )

        user.password_hash = hash_password(new_password)
        self.password_reset_tokens.consume(record)
        self.password_reset_tokens.invalidate_for_user(user.id)
        self.refresh_tokens.revoke_all_for_user(user.id)
        self.audit.add(
            actor_user_id=user.id,
            action="auth.password_reset",
            entity_type="user",
            entity_id=user.id,
            details={"email": user.email, "role": user.role},
            ip_address=ip_address,
        )
        self.db.flush()
        return user

    def change_password(
        self,
        *,
        user: User,
        current_password: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> User:
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        if verify_password(new_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from your current password",
            )
        user.password_hash = hash_password(new_password)
        self.refresh_tokens.revoke_all_for_user(user.id)
        self.audit.add(
            actor_user_id=user.id,
            action="auth.password_changed",
            entity_type="user",
            entity_id=user.id,
            details={"email": user.email, "role": user.role},
            ip_address=ip_address,
        )
        self.db.flush()
        return user
