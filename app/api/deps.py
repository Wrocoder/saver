from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.models import AllocationStrategyRecord, UserProfileRecord, UserRecord
from app.db.session import get_db
from app.repositories.analytics import AnalyticsRepository
from app.repositories.audit import AuditLogRepository
from app.repositories.csv_io import CsvDataRepository
from app.repositories.currency import CurrencyRepository
from app.repositories.export import UserExportRepository
from app.repositories.finance import FinanceRepository
from app.repositories.notifications import NotificationsRepository
from app.repositories.recurring import RecurringRulesRepository
from app.repositories.reports import MonthlyReportsRepository
from app.repositories.sqlalchemy import GoalsRepository


def ensure_demo_user(db: Session) -> UserRecord:
    user = db.scalar(select(UserRecord).where(UserRecord.email == settings.demo_user_email))
    if user is not None:
        return user

    user = UserRecord(email=settings.demo_user_email)
    db.add(user)
    db.flush()

    db.add(
        UserProfileRecord(
            user_id=user.id,
            name="Demo User",
            base_currency="USD",
        )
    )
    db.add(AllocationStrategyRecord(user_id=user.id))
    db.commit()
    db.refresh(user)
    return user


def get_current_user_id(
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
) -> str:
    if authorization:
        user_id = user_id_from_authorization_header(authorization)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid access token")
        user = db.get(UserRecord, user_id)
        if user is None or user.deleted_at is not None:
            raise HTTPException(status_code=401, detail="Unknown user")
        return user.id

    if not settings.dev_auth_fallback_enabled:
        raise HTTPException(status_code=401, detail="Missing access token")

    if x_user_id:
        user = db.get(UserRecord, x_user_id)
        if user is None or user.deleted_at is not None:
            raise HTTPException(status_code=401, detail="Unknown user")
        return user.id

    return ensure_demo_user(db).id


def user_id_from_authorization_header(authorization: str) -> str | None:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return decode_access_token(token)


def get_required_current_user_id(
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing access token")

    user_id = user_id_from_authorization_header(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid access token")

    user = db.get(UserRecord, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user.id


def get_repository(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> GoalsRepository:
    return GoalsRepository(db=db, user_id=user_id)


def get_finance_repository(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> FinanceRepository:
    return FinanceRepository(db=db, user_id=user_id)


def get_currency_repository(
    db: Annotated[Session, Depends(get_db)],
) -> CurrencyRepository:
    return CurrencyRepository(db=db)


def get_analytics_repository(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> AnalyticsRepository:
    return AnalyticsRepository(db=db, user_id=user_id)


def get_audit_log_repository(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> AuditLogRepository:
    return AuditLogRepository(db=db, user_id=user_id)


def get_export_repository(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> UserExportRepository:
    return UserExportRepository(db=db, user_id=user_id)


def get_csv_repository(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> CsvDataRepository:
    return CsvDataRepository(db=db, user_id=user_id)


def get_notifications_repository(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> NotificationsRepository:
    return NotificationsRepository(db=db, user_id=user_id)


def get_recurring_rules_repository(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> RecurringRulesRepository:
    return RecurringRulesRepository(db=db, user_id=user_id)


def get_monthly_reports_repository(
    db: Annotated[Session, Depends(get_db)],
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> MonthlyReportsRepository:
    return MonthlyReportsRepository(db=db, user_id=user_id)
