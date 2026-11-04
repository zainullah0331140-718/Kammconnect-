from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.advertisement import Advertisement
from app.models.provider import ProviderProfile


class AdvertisementRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _with_relations(self, stmt):
        return stmt.options(
            selectinload(Advertisement.provider).selectinload(ProviderProfile.user)
        )

    def get(self, ad_id: int) -> Advertisement | None:
        return self.db.scalar(
            self._with_relations(select(Advertisement).where(Advertisement.id == ad_id))
        )

    def create(self, **values) -> Advertisement:
        ad = Advertisement(**values)
        self.db.add(ad)
        self.db.flush()
        return ad

    def list_by_provider(self, provider_id: int) -> list[Advertisement]:
        return list(
            self.db.scalars(
                self._with_relations(select(Advertisement))
                .where(Advertisement.provider_id == provider_id)
                .order_by(Advertisement.created_at.desc())
            ).all()
        )

    def list_admin(
        self,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Advertisement], int]:
        stmt = self._with_relations(select(Advertisement)).order_by(
            Advertisement.created_at.desc()
        )
        if status:
            stmt = stmt.where(Advertisement.status == status)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        ads = list(
            self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        )
        return ads, total

    def public_active(self, *, limit: int = 6) -> list[Advertisement]:
        today = date.today()
        return list(
            self.db.scalars(
                self._with_relations(select(Advertisement))
                .where(
                    Advertisement.status == "approved",
                    Advertisement.start_date <= today,
                    Advertisement.end_date >= today,
                )
                .order_by(Advertisement.created_at.desc())
                .limit(limit)
            ).all()
        )

    def count_pending(self) -> int:
        return (
            self.db.scalar(
                select(func.count(Advertisement.id)).where(
                    Advertisement.status == "pending"
                )
            )
            or 0
        )
