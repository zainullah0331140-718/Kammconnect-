from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.complaint import Complaint


class ComplaintRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _with_relations(self, stmt):
        return stmt.options(
            selectinload(Complaint.user),
            selectinload(Complaint.provider),
        )

    def get(self, complaint_id: int) -> Complaint | None:
        return self.db.scalar(
            self._with_relations(select(Complaint).where(Complaint.id == complaint_id))
        )

    def create(self, **values) -> Complaint:
        complaint = Complaint(**values)
        self.db.add(complaint)
        self.db.flush()
        return complaint

    def list_by_user(self, user_id: int) -> list[Complaint]:
        return list(
            self.db.scalars(
                self._with_relations(select(Complaint))
                .where(Complaint.user_id == user_id)
                .order_by(Complaint.created_at.desc())
            ).all()
        )

    def list_admin(
        self,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Complaint], int]:
        stmt = self._with_relations(select(Complaint)).order_by(Complaint.created_at.desc())
        if status:
            stmt = stmt.where(Complaint.status == status)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        complaints = list(
            self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        )
        return complaints, total

    def count_open(self) -> int:
        return (
            self.db.scalar(
                select(func.count(Complaint.id)).where(
                    Complaint.status.in_(["open", "in_review"])
                )
            )
            or 0
        )
