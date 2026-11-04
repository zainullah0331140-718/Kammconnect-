from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.v1.routes.auth import clear_auth_cookies
from app.db.session import get_db
from app.dependencies.auth import CurrentUser, get_client_ip
from app.models.enums import UserRole
from app.repositories.complaints import ComplaintRepository
from app.repositories.favorites import FavoriteRepository
from app.repositories.reviews import ReviewRepository
from app.schemas.user import AccountDeleteRequest, UserPublic, UserUpdate
from app.services.serializers import user_public
from app.services.upload_service import delete_image_file, save_image_upload
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserPublic)
def get_me(user: CurrentUser) -> UserPublic:
    return user_public(user)


@router.patch("/me", response_model=UserPublic)
def update_me(
    data: UserUpdate, user: CurrentUser, db: Session = Depends(get_db)
) -> UserPublic:
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user_public(user)


@router.post("/me/image", response_model=UserPublic)
async def upload_my_image(
    user: CurrentUser,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UserPublic:
    new_path = await save_image_upload(file, "profiles")
    old_path = user.profile_image
    user.profile_image = new_path
    db.commit()
    db.refresh(user)
    if old_path and old_path != new_path:
        delete_image_file(old_path)
    return user_public(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    data: AccountDeleteRequest,
    request: Request,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> Response:
    image_paths = UserService(db).delete_account(
        user=user, password=data.password, ip_address=get_client_ip(request)
    )
    db.commit()
    for image_path in image_paths:
        delete_image_file(image_path)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


@router.get("/me/summary")
def my_summary(user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    favorites = FavoriteRepository(db).count_for_customer(user.id)
    reviews, review_count = ReviewRepository(db).list_by_customer(user.id, page=1, page_size=1)
    complaints = ComplaintRepository(db).list_by_user(user.id)
    summary = {
        "user": user_public(user).model_dump(),
        "favorite_count": favorites,
        "review_count": review_count,
        "complaint_count": len(complaints),
        "open_complaint_count": len(
            [c for c in complaints if c.status in {"open", "in_review"}]
        ),
    }
    if user.role == UserRole.PROVIDER.value:
        from app.repositories.advertisements import AdvertisementRepository
        from app.repositories.providers import ProviderRepository
        from app.repositories.services import ServiceRepository

        profile = ProviderRepository(db).get_by_user_id(user.id)
        if profile is not None:
            services = ServiceRepository(db).list_by_provider(
                profile.id, active_only=False
            )
            ads = AdvertisementRepository(db).list_by_provider(profile.id)
            summary["provider"] = {
                "id": profile.id,
                "business_name": profile.business_name,
                "verification_status": profile.verification_status,
                "service_count": len(services),
                "pending_ad_count": len([a for a in ads if a.status == "pending"]),
            }
            summary["rating"] = ProviderRepository(db).rating_summary(
                profile.id, include_pending=True
            )
    return summary
