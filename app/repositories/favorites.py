from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.favorite import Favorite
from app.models.provider import ProviderProfile, ProviderService


class FavoriteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, customer_id: int, provider_id: int) -> Favorite | None:
        return self.db.scalar(
            select(Favorite).where(
                Favorite.customer_id == customer_id,
                Favorite.provider_id == provider_id,
            )
        )

    def create(self, customer_id: int, provider_id: int) -> Favorite:
        favorite = Favorite(customer_id=customer_id, provider_id=provider_id)
        self.db.add(favorite)
        self.db.flush()
        return favorite

    def list_by_customer(self, customer_id: int) -> list[Favorite]:
        return list(
            self.db.scalars(
                select(Favorite)
                .where(Favorite.customer_id == customer_id)
                .options(
                    selectinload(Favorite.provider).selectinload(ProviderProfile.user),
                    selectinload(Favorite.provider)
                    .selectinload(ProviderProfile.services)
                    .selectinload(ProviderService.category),
                )
                .order_by(Favorite.created_at.desc())
            ).all()
        )

    def delete(self, favorite: Favorite) -> None:
        self.db.delete(favorite)

    def count_for_customer(self, customer_id: int) -> int:
        return (
            self.db.scalar(
                select(func.count(Favorite.id)).where(Favorite.customer_id == customer_id)
            )
            or 0
        )

    def count_all(self) -> int:
        return self.db.scalar(select(func.count(Favorite.id))) or 0
