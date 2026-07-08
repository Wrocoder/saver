from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_recurring_rules_repository
from app.api.schemas import (
    ContributionResponse,
    RecurringRuleCreate,
    RecurringRuleResponse,
    RecurringRuleUpdate,
)
from app.db.models import RecurringRuleRecord
from app.domain.models import GoalContribution
from app.repositories.recurring import RecurringRulesRepository


router = APIRouter(prefix="/api", tags=["recurring-rules"])


@router.get("/recurring-rules", response_model=list[RecurringRuleResponse])
def list_recurring_rules(
    active_only: bool = False,
    repo: RecurringRulesRepository = Depends(get_recurring_rules_repository),
) -> list[RecurringRuleRecord]:
    return repo.list_rules(active_only=active_only)


@router.post(
    "/recurring-rules",
    response_model=RecurringRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recurring_rule(
    payload: RecurringRuleCreate,
    repo: RecurringRulesRepository = Depends(get_recurring_rules_repository),
) -> RecurringRuleRecord:
    try:
        return repo.create_rule(
            goal_id=payload.goal_id,
            title=payload.title,
            amount=payload.amount,
            currency=payload.currency,
            frequency=payload.frequency.value,
            day_of_month=payload.day_of_month,
            source=payload.source,
            next_run_on=payload.next_run_on,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/recurring-rules/{rule_id}", response_model=RecurringRuleResponse)
def update_recurring_rule(
    rule_id: str,
    payload: RecurringRuleUpdate,
    repo: RecurringRulesRepository = Depends(get_recurring_rules_repository),
) -> RecurringRuleRecord:
    try:
        record = repo.update_rule(rule_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="Recurring rule not found")
    return record


@router.delete("/recurring-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_rule(
    rule_id: str,
    repo: RecurringRulesRepository = Depends(get_recurring_rules_repository),
) -> None:
    if not repo.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="Recurring rule not found")


@router.post("/recurring-rules/{rule_id}/apply", response_model=ContributionResponse)
def apply_recurring_rule(
    rule_id: str,
    occurred_at: date | None = None,
    repo: RecurringRulesRepository = Depends(get_recurring_rules_repository),
) -> GoalContribution:
    try:
        return repo.apply_rule(rule_id, occurred_at=occurred_at)
    except ValueError as exc:
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
