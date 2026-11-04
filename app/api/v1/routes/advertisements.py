from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.security import validate_external_url
from app.db.session import get_db
from app.dependencies.auth import get_provider_profile
from app.models.provider import ProviderProfile
from app.repositories.advertisements import AdvertisementRepository
from app.schemas.advertisement import AdvertisementOut
from app.services.serializers import advertisement_out
from app.services.upload_service import delete_image_file, save_image_upload

router = APIRouter(prefix="/advertisements", tags=["Advertisements"])


@router.get("/public", response_model=list[AdvertisementOut])
def public_advertisements(
    limit: int = 6, db: Session = Depends(get_db)
) -> list[AdvertisementOut]:
    limit = max(1, min(limit, 12))
    ads = AdvertisementRepository(db).public_active(limit=limit)
    return [advertisement_out(ad) for ad in ads]


@router.get("/me", response_model=list[AdvertisementOut])
def my_advertisements(
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> list[AdvertisementOut]:
    ads = AdvertisementRepository(db).list_by_provider(profile.id)
    return [advertisement_out(ad) for ad in ads]


@router.post("", response_model=AdvertisementOut, status_code=status.HTTP_201_CREATED)
async def create_advertisement(
    title: str = Form(..., min_length=2, max_length=180),
    description: str = Form(..., min_length=10, max_length=3000),
    destination_url: str = Form(..., min_length=1, max_length=500),
    start_date: date = Form(...),
    end_date: date = Form(...),
    image: UploadFile = File(...),
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> AdvertisementOut:
    title = title.strip()
    description = description.strip()
    if len(title) < 2:
        raise HTTPException(status_code=422, detail="Title is too short")
    if len(description) < 10:
        raise HTTPException(status_code=422, detail="Description is too short")
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="End date must be after the start date")
    if end_date < date.today():
        raise HTTPException(status_code=422, detail="End date cannot be in the past")
    try:
        destination_url = validate_external_url(destination_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    image_path = await save_image_upload(image, "ads")
    ad = AdvertisementRepository(db).create(
        provider_id=profile.id,
        title=title,
        description=description,
        image_path=image_path,
        destination_url=destination_url,
        start_date=start_date,
        end_date=end_date,
        status="pending",
    )
    db.commit()
    ad = AdvertisementRepository(db).get(ad.id)
    return advertisement_out(ad)


@router.delete("/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_advertisement(
    ad_id: int,
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> Response:
    repo = AdvertisementRepository(db)
    ad = repo.get(ad_id)
    if ad is None or ad.provider_id != profile.id:
        raise HTTPException(status_code=404, detail="Advertisement not found")
    image_path = ad.image_path
    db.delete(ad)
    db.commit()
    delete_image_file(image_path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
