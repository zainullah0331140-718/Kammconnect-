from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import (
    CurrentUser,
    OptionalUser,
    PaginationParams,
    get_provider_profile,
    require_provider,
)
from app.models.provider import ProviderProfile
from app.repositories.categories import CategoryRepository
from app.repositories.providers import ProviderRepository
from app.schemas.common import Page, paginate
from app.schemas.provider import (
    LocationOut,
    ProviderDetail,
    ProviderOwner,
    ProviderSummary,
)
from app.schemas.service import ProviderProfileCreate, ProviderProfileUpdate
from app.services.provider_service import ProviderServiceLayer
from app.services.serializers import provider_summary
from app.services.upload_service import delete_image_file, save_image_upload

router = APIRouter(prefix="/providers", tags=["Providers"])


def _resolve_category(db: Session, category: str) -> int:
    repo = CategoryRepository(db)
    if category.isdigit():
        found = repo.get(int(category))
    else:
        found = repo.get_by_slug(category)
    if found is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return found.id


@router.get("/featured", response_model=list[ProviderSummary])
def featured_providers(
    limit: int = Query(6, ge=1, le=12), db: Session = Depends(get_db)
) -> list[ProviderSummary]:
    repo = ProviderRepository(db)
    rows, _ = repo.search(verified=True, sort="rating", page=1, page_size=limit)
    return [provider_summary(provider, avg, count) for provider, avg, count in rows]


@router.get("/recent", response_model=list[ProviderSummary])
def recent_providers(
    limit: int = Query(8, ge=1, le=12), db: Session = Depends(get_db)
) -> list[ProviderSummary]:
    repo = ProviderRepository(db)
    rows, _ = repo.search(sort="newest", page=1, page_size=limit)
    return [provider_summary(provider, avg, count) for provider, avg, count in rows]


@router.get("/locations", response_model=list[LocationOut])
def provider_locations(db: Session = Depends(get_db)) -> list[LocationOut]:
    rows = ProviderRepository(db).locations()
    grouped: dict[str, set[str]] = {}
    for city, area in rows:
        if not city:
            continue
        grouped.setdefault(city, set())
        if area:
            grouped[city].add(area)
    return [
        LocationOut(city=city, areas=sorted(areas)) for city, areas in sorted(grouped.items())
    ]


@router.get("/me", response_model=ProviderOwner)
def my_provider_profile(
    user=Depends(require_provider), db: Session = Depends(get_db)
) -> ProviderOwner:
    return ProviderServiceLayer(db).get_owner_view(user)


@router.post("/me", response_model=ProviderOwner, status_code=status.HTTP_201_CREATED)
def create_my_provider_profile(
    data: ProviderProfileCreate,
    user=Depends(require_provider),
    db: Session = Depends(get_db),
) -> ProviderOwner:
    service = ProviderServiceLayer(db)
    service.create_profile(user, data)
    db.commit()
    return service.get_owner_view(user)


@router.patch("/me", response_model=ProviderOwner)
def update_my_provider_profile(
    data: ProviderProfileUpdate,
    user=Depends(require_provider),
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> ProviderOwner:
    service = ProviderServiceLayer(db)
    service.update_profile(profile, data)
    db.commit()
    return service.get_owner_view(user)


@router.post("/me/image", response_model=ProviderOwner)
async def upload_profile_image(
    file: UploadFile = File(...),
    user=Depends(require_provider),
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> ProviderOwner:
    new_path = await save_image_upload(file, "profiles")
    old_path = profile.profile_image
    profile.profile_image = new_path
    db.commit()
    if old_path and old_path != new_path:
        delete_image_file(old_path)
    return ProviderServiceLayer(db).get_owner_view(user)


@router.post("/me/work-images", response_model=ProviderOwner)
async def upload_work_images(
    files: list[UploadFile] = File(...),
    user=Depends(require_provider),
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> ProviderOwner:
    service = ProviderServiceLayer(db)
    await service.add_work_images(profile, files)
    db.commit()
    db.expire_all()
    return service.get_owner_view(user)


@router.delete("/me/work-images/{image_id}", response_model=ProviderOwner)
def delete_work_image(
    image_id: int,
    user=Depends(require_provider),
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> ProviderOwner:
    service = ProviderServiceLayer(db)
    image_path = service.delete_work_image(profile, image_id)
    db.commit()
    delete_image_file(image_path)
    db.expire_all()
    return service.get_owner_view(user)


@router.get("", response_model=Page[ProviderSummary])
def search_providers(
    pagination: PaginationParams,
    q: str | None = Query(None, max_length=120),
    category: str | None = Query(None, max_length=120),
    city: str | None = Query(None, max_length=100),
    area: str | None = Query(None, max_length=100),
    min_rating: float = Query(0, ge=0, le=5),
    verified: bool | None = None,
    sort: Literal["rating", "newest", "name"] = "rating",
    db: Session = Depends(get_db),
) -> dict:
    category_id = _resolve_category(db, category) if category else None
    repo = ProviderRepository(db)
    rows, total = repo.search(
        q=q,
        category_id=category_id,
        city=city,
        area=area,
        min_rating=min_rating,
        verified=verified,
        sort=sort,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    items = [
        provider_summary(provider, avg, count) for provider, avg, count in rows
    ]
    return paginate(items, total, pagination.page, pagination.page_size)


@router.get("/{provider_id}", response_model=ProviderDetail)
def get_provider(
    provider_id: int,
    viewer: OptionalUser = None,
    db: Session = Depends(get_db),
) -> ProviderDetail:
    return ProviderServiceLayer(db).get_public_view(provider_id, viewer)
