from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_provider_profile
from app.models.provider import ProviderProfile
from app.schemas.service import ServiceCreate, ServiceOut, ServiceUpdate
from app.services.provider_service import ProviderServiceLayer

router = APIRouter(prefix="/provider-services", tags=["Provider services"])


@router.get("/me", response_model=list[ServiceOut])
def my_services(
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> list[ServiceOut]:
    return ProviderServiceLayer(db).list_own_services(profile)


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    data: ServiceCreate,
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> ServiceOut:
    service = ProviderServiceLayer(db)
    result = service.create_service(profile, data)
    db.commit()
    return result


@router.get("/provider/{provider_id}", response_model=list[ServiceOut])
def public_provider_services(
    provider_id: int, db: Session = Depends(get_db)
) -> list[ServiceOut]:
    return ProviderServiceLayer(db).public_services(provider_id)


@router.patch("/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: int,
    data: ServiceUpdate,
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> ServiceOut:
    service = ProviderServiceLayer(db)
    result = service.update_service(profile, service_id, data)
    db.commit()
    return result


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    profile: ProviderProfile = Depends(get_provider_profile),
    db: Session = Depends(get_db),
) -> Response:
    service = ProviderServiceLayer(db)
    service.delete_service(profile, service_id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
