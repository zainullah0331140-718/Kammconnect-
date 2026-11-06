from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.enums import ReviewStatus, VerificationStatus
from app.models.review import Review
from app.models.user import User
from app.repositories.favorites import FavoriteRepository
from app.repositories.providers import ProviderRepository
from app.schemas.provider import ProviderSummary
from app.services.serializers import provider_summary

router = APIRouter(prefix="/favorites", tags=["Favorites"])


def _rating_map(db: Session, provider_ids: list[int]) -> dict[int, tuple[float, int]]:
    if not provider_ids:
        return {}
    rows = db.execute(
        select(
            Review.provider_id,
            func.avg(Review.rating),
            func.count(Review.id),
        )
        .where(
            Review.provider_id.in_(provider_ids),
            Review.status == ReviewStatus.APPROVED.value,
        )
        .group_by(Review.provider_id)
    ).all()
    return {row[0]: (float(row[1] or 0), int(row[2] or 0)) for row in rows}


@router.get("/me", response_model=list[ProviderSummary])
def my_favorites(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ProviderSummary]:
    favorites = FavoriteRepository(db).list_by_customer(user.id)
    ratings = _rating_map(db, [favorite.provider_id for favorite in favorites])
    items = []
    for favorite in favorites:
        provider = favorite.provider
        if provider is None or provider.verification_status == VerificationStatus.REJECTED.value:
            continue
        average, count = ratings.get(provider.id, (0.0, 0))
        items.append(provider_summary(provider, average, count))
    return items


@router.post("/{provider_id}", status_code=status.HTTP_201_CREATED)
def add_favorite(
    provider_id: int,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    providers = ProviderRepository(db)
    provider = providers.get(provider_id)
    if provider is None or provider.verification_status == VerificationStatus.REJECTED.value:
        raise HTTPException(status_code=404, detail="Provider not found")
    repo = FavoriteRepository(db)
    existing = repo.get(user.id, provider_id)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return {"message": "Provider is already in your favorites", "is_favorite": True}
    repo.create(user.id, provider_id)
    db.commit()
    return {"message": "Provider added to favorites", "is_favorite": True}


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    provider_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    repo = FavoriteRepository(db)
    favorite = repo.get(user.id, provider_id)
    if favorite is not None:
        repo.delete(favorite)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
