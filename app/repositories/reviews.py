from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.review import Review


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _with_relations(self, stmt):
        return stmt.options(
            selectinload(Review.customer),
            selectinload(Review.provider),
        )

    def get(self, review_id: int) -> Review | None:
        return self.db.scalar(
            self._with_relations(select(Review).where(Review.id == review_id))
        )

    def get_for_customer_provider(self, customer_id: int, provider_id: int) -> Review | None:
        return self.db.scalar(
            select(Review).where(
                Review.customer_id == customer_id, Review.provider_id == provider_id
            )
        )

    def create(self, **values) -> Review:
        review = Review(**values)
        self.db.add(review)
        self.db.flush()
        return review

    def list_by_provider(
        self,
        provider_id: int,
        *,
        status: str | None = "approved",
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Review], int]:
        stmt = (
            self._with_relations(select(Review).where(Review.provider_id == provider_id))
            .order_by(Review.created_at.desc())
        )
        if status:
            stmt = stmt.where(Review.status == status)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        reviews = list(
            self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        )
        return reviews, total

    def list_by_customer(
        self, customer_id: int, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Review], int]:
        stmt = (
            self._with_relations(select(Review).where(Review.customer_id == customer_id))
            .order_by(Review.created_at.desc())
        )
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        reviews = list(
            self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        )
        return reviews, total

    def list_admin(
        self,
        *,
        status: str | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Review], int]:
        stmt = self._with_relations(select(Review)).order_by(Review.created_at.desc())
        if status:
            stmt = stmt.where(Review.status == status)
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(Review.comment.ilike(pattern))
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        reviews = list(
            self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        )
        return reviews, total

    def count_by_status(self, status: str) -> int:
        return (
            self.db.scalar(select(func.count(Review.id)).where(Review.status == status)) or 0
        )
