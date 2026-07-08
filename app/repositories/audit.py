from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLogRecord


class AuditLogRepository:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def list_entries(self, limit: int = 50, entity_type: str | None = None) -> list[AuditLogRecord]:
        statement = select(AuditLogRecord).where(AuditLogRecord.actor_user_id == self.user_id)
        if entity_type:
            statement = statement.where(AuditLogRecord.entity_type == entity_type)
        return list(
            self.db.scalars(
                statement.order_by(AuditLogRecord.created_at.desc(), AuditLogRecord.id.desc()).limit(limit)
            )
        )
