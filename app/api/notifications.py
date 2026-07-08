from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_finance_repository,
    get_notifications_repository,
    get_repository,
)
from app.api.schemas import (
    NotificationResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
)
from app.db.models import NotificationRecord
from app.domain.planning import FinancialPlanResult, build_financial_plan
from app.repositories.finance import FinanceRepository
from app.repositories.notifications import NotificationsRepository
from app.repositories.sqlalchemy import GoalsRepository


router = APIRouter(prefix="/api", tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    status_filter: str | None = None,
    limit: int = 50,
    auto_schedule: bool = True,
    notifications_repo: NotificationsRepository = Depends(get_notifications_repository),
    goals_repo: GoalsRepository = Depends(get_repository),
    finance_repo: FinanceRepository = Depends(get_finance_repository),
) -> list[NotificationRecord]:
    if auto_schedule:
        run_due_notification_schedule(
            notifications_repo=notifications_repo,
            goals_repo=goals_repo,
            finance_repo=finance_repo,
        )
    return notifications_repo.list_notifications(status=status_filter, limit=min(max(limit, 1), 200))


@router.post(
    "/notifications/generate",
    response_model=list[NotificationResponse],
    status_code=status.HTTP_201_CREATED,
)
def generate_notifications(
    notifications_repo: NotificationsRepository = Depends(get_notifications_repository),
    goals_repo: GoalsRepository = Depends(get_repository),
    finance_repo: FinanceRepository = Depends(get_finance_repository),
) -> list[NotificationRecord]:
    try:
        plan = build_current_plan(goals_repo, finance_repo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return notifications_repo.generate_from_plan(plan)


def run_due_notification_schedule(
    notifications_repo: NotificationsRepository,
    goals_repo: GoalsRepository,
    finance_repo: FinanceRepository,
) -> list[NotificationRecord]:
    if not notifications_repo.scheduler_due():
        return []
    if not notifications_repo.get_settings()["in_app_enabled"]:
        return []

    try:
        plan = build_current_plan(goals_repo, finance_repo)
    except ValueError as exc:
        notifications_repo.record_scheduler_run(created_count=0, skipped_reason=str(exc))
        return []

    return notifications_repo.run_scheduler_from_plan(plan)


def build_current_plan(
    goals_repo: GoalsRepository,
    finance_repo: FinanceRepository,
) -> FinancialPlanResult:
    settings = goals_repo.get_plan_settings()
    summary = finance_repo.build_summary()
    goals, currency_conflicts = goals_repo.list_goals_for_planning_with_warnings()
    plan = build_financial_plan(
        goals=goals,
        monthly_available_amount=summary.effective_monthly_available_amount,
        strategy=settings.strategy,
    )
    plan.conflicts = [*currency_conflicts, *plan.conflicts]
    return plan


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: str,
    repo: NotificationsRepository = Depends(get_notifications_repository),
) -> NotificationRecord:
    record = repo.mark_read(notification_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return record


@router.post("/notifications/{notification_id}/dismiss", response_model=NotificationResponse)
def dismiss_notification(
    notification_id: str,
    repo: NotificationsRepository = Depends(get_notifications_repository),
) -> NotificationRecord:
    record = repo.dismiss(notification_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return record


@router.get("/notification-settings", response_model=NotificationSettingsResponse)
def get_notification_settings(
    repo: NotificationsRepository = Depends(get_notifications_repository),
) -> dict[str, Any]:
    return repo.get_settings()


@router.patch("/notification-settings", response_model=NotificationSettingsResponse)
def update_notification_settings(
    payload: NotificationSettingsUpdate,
    repo: NotificationsRepository = Depends(get_notifications_repository),
) -> dict[str, Any]:
    return repo.update_settings(payload.model_dump(exclude_unset=True))
