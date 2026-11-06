from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from app.models.advertisement import Advertisement
from app.models.category import ServiceCategory
from app.models.complaint import Complaint
from app.models.enums import UserRole, VerificationStatus
from app.models.provider import ProviderProfile
from app.models.review import Review
from app.models.user import User
from app.repositories.advertisements import AdvertisementRepository
from app.repositories.audit import AuditRepository
from app.repositories.categories import CategoryRepository
from app.repositories.complaints import ComplaintRepository
from app.repositories.favorites import FavoriteRepository
from app.repositories.providers import ProviderRepository
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.reviews import ReviewRepository
from app.repositories.users import UserRepository
from app.schemas.admin import AdminStats
from app.schemas.category import CategoryCreate, CategoryUpdate, slugify
from app.schemas.provider import VerificationUpdate
from app.schemas.user import AdminUserOut, AdminUserUpdate
from app.services.serializers import (
    admin_review_out,
    advertisement_out,
    audit_out,
    provider_owner,
    user_public,
)


class AdminService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.providers = ProviderRepository(db)
        self.categories = CategoryRepository(db)
        self.reviews = ReviewRepository(db)
        self.complaints = ComplaintRepository(db)
        self.ads = AdvertisementRepository(db)
        self.favorites = FavoriteRepository(db)
        self.audit = AuditRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    def stats(self) -> AdminStats:
        recent_logs, _ = self.audit.list(page=1, page_size=8)
        verification = self.providers.verification_counts()
        active_categories = len(
            [category for category in self.categories.list_all() if category.is_active]
        )
        return AdminStats(
            total_users=self.users.count_all(),
            total_customers=self.users.count_by_role(UserRole.CUSTOMER.value),
            total_providers=self.users.count_by_role(UserRole.PROVIDER.value),
            total_admins=self.users.count_by_role(UserRole.ADMIN.value),
            verified_providers=verification.get(VerificationStatus.VERIFIED.value, 0),
            pending_providers=verification.get(VerificationStatus.PENDING.value, 0),
            rejected_providers=verification.get(VerificationStatus.REJECTED.value, 0),
            pending_reviews=self.reviews.count_by_status("pending"),
            open_complaints=self.complaints.count_open(),
            pending_ads=self.ads.count_pending(),
            active_categories=active_categories,
            total_favorites=self.favorites.count_all(),
            recent_audit=[audit_out(log) for log in recent_logs],
        )

    def list_users(self, *, role: str | None, q: str | None, page: int, page_size: int):
        users, total = self.users.list(role=role, q=q, page=page, page_size=page_size)
        logins = self.users.login_stats([user.id for user in users])
        items = []
        for user in users:
            profile = user.provider_profile
            base = user_public(user).model_dump()
            last_login_at, login_count = logins.get(user.id, (None, 0))
            items.append(
                AdminUserOut(
                    **base,
                    provider_id=profile.id if profile else None,
                    business_name=profile.business_name if profile else None,
                    verification_status=profile.verification_status if profile else None,
                    last_login_at=last_login_at,
                    login_count=login_count,
                ).model_dump()
            )
        return items, total

    def update_user(
        self,
        *,
        admin: User,
        user_id: int,
        data: AdminUserUpdate,
        ip_address: str | None,
    ) -> dict:
        target = self.users.get(user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        if target.id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot change your own role or status here",
            )
        payload = data.model_dump(exclude_unset=True)
        new_role = payload.get("role", target.role)
        new_active = payload.get("is_active", target.is_active)

        losing_active_admin = (
            target.role == UserRole.ADMIN.value
            and target.is_active
            and (new_role != UserRole.ADMIN.value or not new_active)
        )
        if losing_active_admin and self.users.count_active_admins() <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one active administrator must remain",
            )

        changes: dict = {}
        if "role" in payload and payload["role"] != target.role:
            changes["role"] = {"from": target.role, "to": payload["role"]}
            target.role = payload["role"]
        if "is_active" in payload and bool(payload["is_active"]) != target.is_active:
            changes["is_active"] = {"from": target.is_active, "to": bool(payload["is_active"])}
            target.is_active = bool(payload["is_active"])
            if not target.is_active:
                self.refresh_tokens.revoke_all_for_user(target.id)

        self.audit.add(
            actor_user_id=admin.id,
            action="admin.user.update",
            entity_type="user",
            entity_id=target.id,
            details=changes,
            ip_address=ip_address,
        )
        self.db.flush()
        profile = target.provider_profile
        base = user_public(target).model_dump()
        last_login_at, login_count = self.users.login_stats([target.id]).get(
            target.id, (None, 0)
        )
        return AdminUserOut(
            **base,
            provider_id=profile.id if profile else None,
            business_name=profile.business_name if profile else None,
            verification_status=profile.verification_status if profile else None,
            last_login_at=last_login_at,
            login_count=login_count,
        ).model_dump()

    def delete_user(
        self, *, admin: User, user_id: int, ip_address: str | None
    ) -> list[str]:
        target = self.users.get(user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        if target.id == admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot delete your own account",
            )
        if (
            target.role == UserRole.ADMIN.value
            and target.is_active
            and self.users.count_active_admins() <= 1
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one active administrator must remain",
            )

        profile = target.provider_profile
        image_paths: list[str] = []
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
            actor_user_id=admin.id,
            action="admin.user.delete",
            entity_type="user",
            entity_id=target.id,
            details={
                "email": target.email,
                "role": target.role,
                "provider_id": profile.id if profile else None,
            },
            ip_address=ip_address,
        )
        self.db.delete(target)
        self.db.flush()
        return image_paths

    def list_verification_providers(
        self, *, status_filter: str | None, q: str | None, page: int, page_size: int
    ):
        providers, total = self.providers.list_admin(
            status=status_filter, q=q, page=page, page_size=page_size
        )
        items = [self.admin_provider_dict(provider) for provider in providers]
        return items, total

    def admin_provider_dict(self, provider: ProviderProfile) -> dict:
        summary = self.providers.rating_summary(provider.id, include_pending=True)
        data = provider_owner(
            provider, summary["average_rating"], summary["review_count"]
        ).model_dump()
        data["pending_reviews"] = summary.get("pending_count", 0)
        data["provider_email"] = provider.user.email if provider.user else ""
        return data

    def set_verification(
        self,
        *,
        admin: User,
        provider_id: int,
        data: VerificationUpdate,
        ip_address: str | None,
    ) -> dict:
        provider = self.providers.get(provider_id)
        if provider is None:
            raise HTTPException(status_code=404, detail="Provider not found")
        old_status = provider.verification_status
        provider.verification_status = data.status
        provider.verification_note = data.note
        from app.models.mixins import utcnow

        provider.verified_at = utcnow() if data.status == "verified" else None
        self.audit.add(
            actor_user_id=admin.id,
            action="provider.verification",
            entity_type="provider_profile",
            entity_id=provider.id,
            details={"from": old_status, "to": data.status, "note": data.note},
            ip_address=ip_address,
        )
        self.db.flush()
        return self.admin_provider_dict(provider)

    def list_categories(self):
        counts = self.categories.provider_counts()
        return [
            {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "description": category.description,
                "icon": category.icon,
                "is_active": category.is_active,
                "provider_count": counts.get(category.id, 0),
            }
            for category in self.categories.list_all()
        ]

    def create_category(
        self, *, admin: User, data: CategoryCreate, ip_address: str | None
    ) -> ServiceCategory:
        if self.categories.get_by_name(data.name) is not None:
            raise HTTPException(status_code=409, detail="A category with this name already exists")
        slug = data.slug or slugify(data.name)
        if not slug:
            raise HTTPException(status_code=422, detail="Enter a valid category name")
        if self.categories.get_by_slug(slug) is not None:
            raise HTTPException(status_code=409, detail="A category with this slug already exists")
        category = self.categories.create(
            name=data.name,
            slug=slug,
            description=data.description,
            icon=data.icon,
            is_active=data.is_active,
        )
        self.audit.add(
            actor_user_id=admin.id,
            action="category.create",
            entity_type="service_category",
            entity_id=category.id,
            details={"name": category.name, "slug": category.slug},
            ip_address=ip_address,
        )
        self.db.flush()
        return category

    def update_category(
        self,
        *,
        admin: User,
        category_id: int,
        data: CategoryUpdate,
        ip_address: str | None,
    ) -> ServiceCategory:
        category = self.categories.get(category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        payload = data.model_dump(exclude_unset=True)
        if "name" in payload and payload["name"]:
            existing = self.categories.get_by_name(payload["name"])
            if existing is not None and existing.id != category.id:
                raise HTTPException(
                    status_code=409, detail="A category with this name already exists"
                )
            category.name = payload["name"]
        if "slug" in payload and payload["slug"]:
            existing = self.categories.get_by_slug(payload["slug"])
            if existing is not None and existing.id != category.id:
                raise HTTPException(
                    status_code=409, detail="A category with this slug already exists"
                )
            category.slug = payload["slug"]
        for field in ("description", "icon", "is_active"):
            if field in payload:
                setattr(category, field, payload[field])
        self.audit.add(
            actor_user_id=admin.id,
            action="category.update",
            entity_type="service_category",
            entity_id=category.id,
            details={"changes": payload},
            ip_address=ip_address,
        )
        self.db.flush()
        return category

    def delete_category(
        self, *, admin: User, category_id: int, ip_address: str | None
    ) -> None:
        category = self.categories.get(category_id)
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found")
        if self.categories.service_count(category.id) > 0:
            raise HTTPException(
                status_code=409,
                detail="This category is in use. Deactivate it instead of deleting it.",
            )
        self.audit.add(
            actor_user_id=admin.id,
            action="category.delete",
            entity_type="service_category",
            entity_id=category.id,
            details={"name": category.name},
            ip_address=ip_address,
        )
        self.db.delete(category)
        self.db.flush()

    def list_reviews(
        self, *, status_filter: str | None, q: str | None, page: int, page_size: int
    ):
        reviews, total = self.reviews.list_admin(
            status=status_filter, q=q, page=page, page_size=page_size
        )
        return [admin_review_out(review).model_dump() for review in reviews], total

    def moderate_review(
        self,
        *,
        admin: User,
        review_id: int,
        new_status: str,
        note: str | None,
        ip_address: str | None,
    ) -> Review:
        review = self.reviews.get(review_id)
        if review is None:
            raise HTTPException(status_code=404, detail="Review not found")
        old_status = review.status
        review.status = new_status
        review.moderation_note = note
        self.audit.add(
            actor_user_id=admin.id,
            action="review.moderate",
            entity_type="review",
            entity_id=review.id,
            details={"from": old_status, "to": new_status, "note": note},
            ip_address=ip_address,
        )
        self.db.flush()
        return review

    def delete_review(
        self, *, admin: User, review_id: int, ip_address: str | None
    ) -> None:
        review = self.reviews.get(review_id)
        if review is None:
            raise HTTPException(status_code=404, detail="Review not found")
        self.audit.add(
            actor_user_id=admin.id,
            action="review.delete",
            entity_type="review",
            entity_id=review.id,
            details={"provider_id": review.provider_id, "rating": review.rating},
            ip_address=ip_address,
        )
        self.db.delete(review)
        self.db.flush()

    def list_complaints(
        self, *, status_filter: str | None, page: int, page_size: int
    ):
        from app.services.serializers import complaint_out

        complaints, total = self.complaints.list_admin(
            status=status_filter, page=page, page_size=page_size
        )
        return [complaint_out(complaint).model_dump() for complaint in complaints], total

    def update_complaint(
        self,
        *,
        admin: User,
        complaint_id: int,
        new_status: str,
        admin_response: str | None,
        ip_address: str | None,
    ) -> Complaint:
        complaint = self.complaints.get(complaint_id)
        if complaint is None:
            raise HTTPException(status_code=404, detail="Complaint not found")
        old_status = complaint.status
        complaint.status = new_status
        complaint.admin_response = admin_response
        self.audit.add(
            actor_user_id=admin.id,
            action="complaint.update",
            entity_type="complaint",
            entity_id=complaint.id,
            details={"from": old_status, "to": new_status},
            ip_address=ip_address,
        )
        self.db.flush()
        return complaint

    def delete_complaint(
        self, *, admin: User, complaint_id: int, ip_address: str | None
    ) -> None:
        complaint = self.complaints.get(complaint_id)
        if complaint is None:
            raise HTTPException(status_code=404, detail="Complaint not found")
        self.audit.add(
            actor_user_id=admin.id,
            action="complaint.delete",
            entity_type="complaint",
            entity_id=complaint.id,
            details={
                "user_id": complaint.user_id,
                "provider_id": complaint.provider_id,
                "subject": complaint.subject,
            },
            ip_address=ip_address,
        )
        self.db.delete(complaint)
        self.db.flush()

    def list_ads(self, *, status_filter: str | None, page: int, page_size: int):
        ads, total = self.ads.list_admin(status=status_filter, page=page, page_size=page_size)
        return [advertisement_out(ad).model_dump() for ad in ads], total

    def moderate_ad(
        self,
        *,
        admin: User,
        ad_id: int,
        new_status: str,
        note: str | None,
        ip_address: str | None,
    ) -> Advertisement:
        ad = self.ads.get(ad_id)
        if ad is None:
            raise HTTPException(status_code=404, detail="Advertisement not found")
        old_status = ad.status
        ad.status = new_status
        ad.admin_note = note
        self.audit.add(
            actor_user_id=admin.id,
            action="advertisement.moderate",
            entity_type="advertisement",
            entity_id=ad.id,
            details={"from": old_status, "to": new_status, "note": note},
            ip_address=ip_address,
        )
        self.db.flush()
        return ad

    def list_audit(self, *, action: str | None, page: int, page_size: int):
        logs, total = self.audit.list(
            action=action, page=page, page_size=page_size
        )
        return [audit_out(log) for log in logs], total

    def clear_audit_logs(
        self, *, admin: User, ip_address: str | None
    ) -> int:
        deleted = self.audit.delete_all()
        self.audit.add(
            actor_user_id=admin.id,
            action="audit.clear",
            entity_type="audit_log",
            details={"deleted": deleted},
            ip_address=ip_address,
        )
        self.db.flush()
        return deleted
