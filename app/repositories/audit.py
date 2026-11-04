import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self,
        *,
        actor_user_id: int | None,
        action: str,
        entity_type: str,
        entity_id: str | int | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=json.dumps(details or {}, ensure_ascii=True),
            ip_address=ip_address,
        )
        self.db.add(log)
        self.db.flush()
        return log

    def list(
        self, *, action: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[AuditLog], int]:
        stmt = (
            select(AuditLog)
            .options(selectinload(AuditLog.actor))
            .order_by(AuditLog.created_at.desc())
        )
        if action:
            stmt = stmt.where(AuditLog.action == action)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        logs = list(
            self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
        )
        return logs, total
