from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.dependencies.auth import (
    PaginationParams,
    get_provider_profile,
    require_customer,
    require_provider,
)
from app.models.enums import ReviewStatus, VerificationStatus
from app.models.provider import ProviderProfile
from app.models.user import User
from app.repositories.providers import ProviderRepository
from app.repositories.reviews import ReviewRepository
from app.schemas.common import Page, paginate
from app.schemas.review import ReviewCreate, ReviewOut, ReviewUpdate
from app.services.serializers import review_out

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("", response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    data: ReviewCreate,
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> ReviewOut:
    providers = ProviderRepository(db)
    provider = providers.get(data.provider_id)
    if provider is None or provider.verification_status == VerificationStatus.REJECTED.value:
        raise HTTPException(status_code=404, detail="Provider not found")
    if provider.user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot review your own business")
    if (
        settings.reviews_require_verified_provider
        and provider.verification_status != VerificationStatus.VERIFIED.value
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reviews are available after this provider is verified",
        )
    reviews = ReviewRepository(db)
    if reviews.get_for_customer_provider(user.id, provider.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this provider",
        )
    review = reviews.create(
        provider_id=provider.id,
        customer_id=user.id,
        rating=data.rating,
        comment=data.comment,
        status=(
            ReviewStatus.PENDING.value
            if settings.reviews_require_approval
            else ReviewStatus.APPROVED.value
        ),
    )
    review.customer = user
    review.provider = provider
    db.commit()
    return review_out(review)


@router.get("", response_model=Page[ReviewOut])
def provider_reviews(
    pagination: PaginationParams,
    provider_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
) -> dict:
    providers = ProviderRepository(db)
    provider = providers.get(provider_id)
    if provider is None or provider.verification_status == VerificationStatus.REJECTED.value:
        raise HTTPException(status_code=404, detail="Provider not found")
    reviews, total = ReviewRepository(db).list_by_provider(
        provider_id,
        status=ReviewStatus.APPROVED.value,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginate(
        [review_out(review) for review in reviews],
        total,
        pagination.page,
        pagination.page_size,
    )


@router.get("/me", response_model=Page[ReviewOut])
def my_reviews(
    pagination: PaginationParams,
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> dict:
    reviews, total = ReviewRepository(db).list_by_customer(
        user.id, page=pagination.page, page_size=pagination.page_size
    )
    return paginate(
        [review_out(review) for review in reviews],
        total,
        pagination.page,
        pagination.page_size,
    )


@router.get("/provider/me", response_model=Page[ReviewOut])
def reviews_for_my_business(
    pagination: PaginationParams,
    review_status: Literal["approved", "pending", "rejected"] | None = Query(
        None, alias="status"
    ),
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> dict:
    reviews, total = ReviewRepository(db).list_by_provider(
        profile.id,
        status=review_status,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return paginate(
        [review_out(review) for review in reviews],
        total,
        pagination.page,
        pagination.page_size,
    )


@router.patch("/{review_id}", response_model=ReviewOut)
def update_review(
    review_id: int,
    data: ReviewUpdate,
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> ReviewOut:
    repo = ReviewRepository(db)
    review = repo.get(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.customer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own reviews",
        )
    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(review, field, value)
    review.status = (
        ReviewStatus.PENDING.value
        if settings.reviews_require_approval
        else ReviewStatus.APPROVED.value
    )
    review.moderation_note = None
    db.commit()
    db.refresh(review)
    return review_out(review)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: int,
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> Response:
    repo = ReviewRepository(db)
    review = repo.get(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.customer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own reviews",
        )
    db.delete(review)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
