from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import UserRole, VerificationStatus
from app.models.provider import ProviderProfile, ProviderService
from app.models.review import Review
from app.models.user import User


def _public_search_statement():
    stats = (
        select(
            Review.provider_id.label("provider_id"),
            func.avg(Review.rating).label("average_rating"),
            func.count(Review.id).label("review_count"),
        )
        .where(Review.status == "approved")
        .group_by(Review.provider_id)
        .subquery()
    )
    return (
        select(
            ProviderProfile,
            func.coalesce(stats.c.average_rating, 0.0),
            func.coalesce(stats.c.review_count, 0),
        )
        .join(User, User.id == ProviderProfile.user_id)
        .outerjoin(stats, stats.c.provider_id == ProviderProfile.id)
        .where(
            User.is_active.is_(True),
            User.role == UserRole.PROVIDER.value,
        )
        .options(
            selectinload(ProviderProfile.user),
            selectinload(ProviderProfile.services).selectinload(ProviderService.category),
        )
    )


class ProviderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, provider_id: int) -> ProviderProfile | None:
        return self.db.get(ProviderProfile, provider_id)

    def get_by_user_id(self, user_id: int) -> ProviderProfile | None:
        return self.db.scalar(
            select(ProviderProfile)
            .where(ProviderProfile.user_id == user_id)
            .options(
                selectinload(ProviderProfile.user),
                selectinload(ProviderProfile.services).selectinload(ProviderService.category),
                selectinload(ProviderProfile.work_images),
            )
        )

    def create(self, user_id: int, **values) -> ProviderProfile:
        profile = ProviderProfile(user_id=user_id, **values)
        self.db.add(profile)
        self.db.flush()
        return profile

    def search(
        self,
        *,
        q: str | None = None,
        category_id: int | None = None,
        city: str | None = None,
        area: str | None = None,
        min_rating: float = 0,
        verified: bool | None = None,
        sort: str = "rating",
        page: int = 1,
        page_size: int = 12,
        exclude_rejected: bool = True,
    ) -> tuple[list[tuple[ProviderProfile, float, int]], int]:
        stmt = _public_search_statement()

        if exclude_rejected:
            stmt = stmt.where(
                ProviderProfile.verification_status != VerificationStatus.REJECTED.value
            )
        if verified is True:
            stmt = stmt.where(
                ProviderProfile.verification_status == VerificationStatus.VERIFIED.value
            )
        elif verified is False:
            stmt = stmt.where(
                ProviderProfile.verification_status != VerificationStatus.VERIFIED.value
            )
        if category_id is not None:
            category_match = (
                select(ProviderService.id)
                .where(
                    ProviderService.provider_id == ProviderProfile.id,
                    ProviderService.category_id == category_id,
                    ProviderService.is_active.is_(True),
                )
                .exists()
            )
            stmt = stmt.where(category_match)
        if city:
            stmt = stmt.where(ProviderProfile.city.ilike(f"%{city.strip()}%"))
        if area:
            stmt = stmt.where(ProviderProfile.area.ilike(f"%{area.strip()}%"))
        if q:
            pattern = f"%{q.strip()}%"
            service_match = (
                select(ProviderService.id)
                .where(
                    ProviderService.provider_id == ProviderProfile.id,
                    ProviderService.is_active.is_(True),
                    ProviderService.title.ilike(pattern),
                )
                .exists()
            )
            stmt = stmt.where(
                or_(
                    ProviderProfile.business_name.ilike(pattern),
                    User.full_name.ilike(pattern),
                    ProviderProfile.description.ilike(pattern),
                    service_match,
                )
            )
        if min_rating and min_rating > 0:
            stats_avg = stmt.column_descriptions[1]["expr"]
            stmt = stmt.where(stats_avg >= min_rating)

        if sort == "newest":
            stmt = stmt.order_by(ProviderProfile.created_at.desc())
        elif sort == "name":
            stmt = stmt.order_by(ProviderProfile.business_name.asc())
        else:
            stmt = stmt.order_by(
                stmt.column_descriptions[1]["expr"].desc(),
                stmt.column_descriptions[2]["expr"].desc(),
                ProviderProfile.created_at.desc(),
            )

        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        rows = self.db.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        ).all()
        return [(row[0], float(row[1] or 0), int(row[2] or 0)) for row in rows], total

    def get_with_stats(self, provider_id: int) -> tuple[ProviderProfile, float, int] | None:
        stmt = (
            _public_search_statement()
            .where(ProviderProfile.id == provider_id)
            .options(selectinload(ProviderProfile.work_images))
        )
        row = self.db.execute(stmt).first()
        if row is None:
            return None
        return row[0], float(row[1] or 0), int(row[2] or 0)

    def list_admin(
        self,
        *,
        status: str | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProviderProfile], int]:
        stmt = (
            select(ProviderProfile)
            .join(User, User.id == ProviderProfile.user_id)
            .options(
                selectinload(ProviderProfile.user),
                selectinload(ProviderProfile.services).selectinload(ProviderService.category),
                selectinload(ProviderProfile.work_images),
            )
            .order_by(ProviderProfile.created_at.desc())
        )
        if status:
            stmt = stmt.where(ProviderProfile.verification_status == status)
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    ProviderProfile.business_name.ilike(pattern),
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        providers = list(
            self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        )
        return providers, total

    def verification_counts(self) -> dict[str, int]:
        rows = self.db.execute(
            select(ProviderProfile.verification_status, func.count(ProviderProfile.id)).group_by(
                ProviderProfile.verification_status
            )
        ).all()
        return {row[0]: row[1] for row in rows}

    def locations(self) -> list[tuple[str, str | None]]:
        return list(
            self.db.execute(
                select(ProviderProfile.city, ProviderProfile.area)
                .join(User, User.id == ProviderProfile.user_id)
                .where(
                    User.is_active.is_(True),
                    User.role == UserRole.PROVIDER.value,
                    ProviderProfile.city.is_not(None),
                    ProviderProfile.verification_status
                    != VerificationStatus.REJECTED.value,
                )
                .distinct()
                .order_by(ProviderProfile.city.asc(), ProviderProfile.area.asc())
            ).all()
        )

    def rating_summary(self, provider_id: int, include_pending: bool = False) -> dict:
        rows = self.db.execute(
            select(Review.rating, func.count(Review.id))
            .where(Review.provider_id == provider_id, Review.status == "approved")
            .group_by(Review.rating)
        ).all()
        distribution = {rating: count for rating, count in rows}
        review_count = sum(distribution.values())
        average = (
            sum(rating * count for rating, count in distribution.items()) / review_count
            if review_count
            else 0.0
        )
        pending = (
            self.db.scalar(
                select(func.count(Review.id)).where(
                    Review.provider_id == provider_id, Review.status == "pending"
                )
            )
            or 0
        )
        result = {
            "average_rating": round(average, 2),
            "review_count": review_count,
            "distribution": {str(i): distribution.get(i, 0) for i in range(1, 6)},
        }
        if include_pending:
            result["pending_count"] = pending
        return result
