from fastapi import APIRouter, Depends

from app.api.deps import get_audit_log_repository
from app.api.schemas import AuditLogResponse
from app.db.models import AuditLogRecord
from app.repositories.audit import AuditLogRepository


router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit-log", response_model=list[AuditLogResponse])
def list_audit_log(
    limit: int = 50,
    entity_type: str | None = None,
    repo: AuditLogRepository = Depends(get_audit_log_repository),
) -> list[AuditLogRecord]:
    return repo.list_entries(limit=min(max(limit, 1), 200), entity_type=entity_type)
