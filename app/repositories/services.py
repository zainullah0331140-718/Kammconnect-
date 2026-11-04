from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.provider import ProviderService


class ServiceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, service_id: int) -> ProviderService | None:
        return self.db.scalar(
            select(ProviderService)
            .where(ProviderService.id == service_id)
            .options(selectinload(ProviderService.category))
        )

    def list_by_provider(
        self, provider_id: int, *, active_only: bool = True
    ) -> list[ProviderService]:
        stmt = (
            select(ProviderService)
            .where(ProviderService.provider_id == provider_id)
            .options(selectinload(ProviderService.category))
            .order_by(ProviderService.created_at.desc())
        )
        if active_only:
            stmt = stmt.where(ProviderService.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def create(self, provider_id: int, **values) -> ProviderService:
        service = ProviderService(provider_id=provider_id, **values)
        self.db.add(service)
        self.db.flush()
        return service

    def delete(self, service: ProviderService) -> None:
        self.db.delete(service)
