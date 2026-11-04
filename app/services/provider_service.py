from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.category import ServiceCategory
from app.models.enums import UserRole, VerificationStatus
from app.models.provider import ProviderProfile, ProviderService, ProviderWorkImage
from app.models.user import User
from app.repositories.categories import CategoryRepository
from app.repositories.favorites import FavoriteRepository
from app.repositories.providers import ProviderRepository
from app.repositories.services import ServiceRepository
from app.schemas.service import (
    ProviderProfileCreate,
    ProviderProfileUpdate,
    ServiceCreate,
    ServiceUpdate,
)
from app.services.serializers import provider_detail, provider_owner, service_out
from app.services.upload_service import delete_image_file, save_image_upload

MAX_WORK_IMAGES = 5


class ProviderServiceLayer:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.providers = ProviderRepository(db)
        self.services = ServiceRepository(db)
        self.categories = CategoryRepository(db)
        self.favorites = FavoriteRepository(db)

    def require_profile(self, user: User) -> ProviderProfile:
        profile = self.providers.get_by_user_id(user.id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Create your provider profile first",
            )
        return profile

    def create_profile(self, user: User, data: ProviderProfileCreate) -> ProviderProfile:
        if self.providers.get_by_user_id(user.id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a provider profile",
            )
        if user.role != UserRole.PROVIDER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only provider accounts can create provider profiles",
            )
        return self.providers.create(
            user_id=user.id,
            business_name=data.business_name,
            description=data.description,
            experience_years=data.experience_years,
            city=data.city,
            area=data.area,
            address=data.address,
            contact_phone=data.contact_phone,
            whatsapp_number=data.whatsapp_number,
        )

    def update_profile(
        self, profile: ProviderProfile, data: ProviderProfileUpdate
    ) -> ProviderProfile:
        payload = data.model_dump(exclude_unset=True)
        for field in ("business_name", "city"):
            if field in payload and not payload[field]:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{field.replace('_', ' ').title()} cannot be empty",
                )
        for key, value in payload.items():
            setattr(profile, key, value)
        self.db.flush()
        return profile

    def get_owner_view(self, user: User) -> dict:
        profile = self.require_profile(user)
        summary = self.providers.rating_summary(profile.id, include_pending=True)
        return provider_owner(
            profile, summary["average_rating"], summary["review_count"]
        ).model_dump()

    def get_public_view(self, provider_id: int, viewer: User | None) -> dict:
        row = self.providers.get_with_stats(provider_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        provider, avg, count = row
        is_owner = viewer is not None and viewer.id == provider.user_id
        is_admin = viewer is not None and viewer.role == UserRole.ADMIN.value
        if (
            provider.verification_status == VerificationStatus.REJECTED.value
            and not is_owner
            and not is_admin
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        if provider.user is None or not provider.user.is_active:
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found"
                )
        is_favorite = False
        if viewer is not None and viewer.role == UserRole.CUSTOMER.value:
            is_favorite = self.favorites.get(viewer.id, provider.id) is not None
        summary = self.providers.rating_summary(provider.id)
        return provider_detail(
            provider,
            avg,
            count,
            is_favorite=is_favorite,
            review_summary=summary,
        ).model_dump()

    async def add_work_images(
        self, profile: ProviderProfile, files: list[UploadFile]
    ) -> None:
        files = [file for file in files if file is not None and file.filename]
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Choose at least one photo to upload",
            )
        current = len(profile.work_images)
        remaining = MAX_WORK_IMAGES - current
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You can add up to {MAX_WORK_IMAGES} work photos. Remove one before uploading another.",
            )
        if len(files) > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You can add {remaining} more work photo{'s' if remaining != 1 else ''}.",
            )

        next_position = max(
            (image.position for image in profile.work_images), default=-1
        ) + 1
        saved_paths: list[str] = []
        try:
            for file in files:
                image_path = await save_image_upload(file, "work")
                saved_paths.append(image_path)
                self.db.add(
                    ProviderWorkImage(
                        provider_id=profile.id,
                        image_path=image_path,
                        position=next_position,
                    )
                )
                next_position += 1
            self.db.flush()
        except Exception:
            self.db.rollback()
            for path in saved_paths:
                delete_image_file(path)
            raise

    def delete_work_image(self, profile: ProviderProfile, image_id: int) -> str:
        image = next(
            (item for item in profile.work_images if item.id == image_id), None
        )
        if image is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Work photo not found"
            )
        image_path = image.image_path
        self.db.delete(image)
        self.db.flush()
        return image_path

    def validate_category(self, category_id: int) -> ServiceCategory:
        category = self.categories.get(category_id)
        if category is None or not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Choose a valid service category",
            )
        return category

    def create_service(self, profile: ProviderProfile, data: ServiceCreate) -> dict:
        category = self.validate_category(data.category_id)
        service = self.services.create(
            provider_id=profile.id,
            category_id=category.id,
            title=data.title,
            description=data.description,
            price_min=data.price_min,
            price_max=data.price_max,
            is_active=data.is_active,
        )
        service.category = category
        return service_out(service).model_dump()

    def update_service(
        self, profile: ProviderProfile, service_id: int, data: ServiceUpdate
    ) -> dict:
        service = self.services.get(service_id)
        if service is None or service.provider_id != profile.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        payload = data.model_dump(exclude_unset=True)
        if "category_id" in payload and payload["category_id"] is not None:
            category = self.validate_category(payload["category_id"])
            service.category = category
            service.category_id = category.id
        for field in ("title", "description", "price_min", "price_max", "is_active"):
            if field in payload:
                setattr(service, field, payload[field])
        if (
            service.price_min is not None
            and service.price_max is not None
            and service.price_min > service.price_max
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Minimum price cannot be greater than maximum price",
            )
        self.db.flush()
        return service_out(service).model_dump()

    def delete_service(self, profile: ProviderProfile, service_id: int) -> None:
        service = self.services.get(service_id)
        if service is None or service.provider_id != profile.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
        self.services.delete(service)
        self.db.flush()

    def list_own_services(self, profile: ProviderProfile) -> list[dict]:
        services = self.services.list_by_provider(profile.id, active_only=False)
        return [service_out(service).model_dump() for service in services]

    def public_services(self, provider_id: int) -> list[dict]:
        provider = self.providers.get(provider_id)
        if provider is None or provider.verification_status == VerificationStatus.REJECTED.value:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        services = self.services.list_by_provider(provider_id, active_only=True)
        return [service_out(service).model_dump() for service in services]
