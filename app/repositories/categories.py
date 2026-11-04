from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import ServiceCategory
from app.models.provider import ProviderProfile, ProviderService


class CategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, category_id: int) -> ServiceCategory | None:
        return self.db.get(ServiceCategory, category_id)

    def get_by_slug(self, slug: str) -> ServiceCategory | None:
        return self.db.scalar(select(ServiceCategory).where(ServiceCategory.slug == slug))

    def get_by_name(self, name: str) -> ServiceCategory | None:
        return self.db.scalar(
            select(ServiceCategory).where(func.lower(ServiceCategory.name) == name.lower())
        )

    def list_active(self) -> list[ServiceCategory]:
        return list(
            self.db.scalars(
                select(ServiceCategory)
                .where(ServiceCategory.is_active.is_(True))
                .order_by(ServiceCategory.name.asc())
            ).all()
        )

    def list_all(self) -> list[ServiceCategory]:
        return list(
            self.db.scalars(select(ServiceCategory).order_by(ServiceCategory.name.asc())).all()
        )

    def create(self, **values) -> ServiceCategory:
        category = ServiceCategory(**values)
        self.db.add(category)
        self.db.flush()
        return category

    def provider_counts(self) -> dict[int, int]:
        rows = self.db.execute(
            select(
                ProviderService.category_id,
                func.count(func.distinct(ProviderService.provider_id)),
            )
            .join(ProviderProfile, ProviderProfile.id == ProviderService.provider_id)
            .where(
                ProviderService.is_active.is_(True),
                ProviderProfile.verification_status == "verified",
            )
            .group_by(ProviderService.category_id)
        ).all()
        return {row[0]: row[1] for row in rows}

    def service_count(self, category_id: int) -> int:
        return (
            self.db.scalar(
                select(func.count(ProviderService.id)).where(
                    ProviderService.category_id == category_id
                )
            )
            or 0
        )
