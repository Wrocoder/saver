from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user_id,
    get_finance_repository,
    get_repository,
    get_required_current_user_id,
)
from app.api.schemas import (
    ContributionCreate,
    ContributionResponse,
    GoalCreate,
    GoalPriceHistoryCreate,
    GoalPriceHistoryResponse,
    GoalResponse,
    GoalUpdate,
    PlanResponse,
    PriorityUpdate,
    ScenarioRequest,
    ScenarioResponse,
    StrategyResponse,
    StrategyUpdate,
    UserCreate,
    UserResponse,
)
from app.core.config import settings
from app.db.models import AllocationStrategyRecord, UserProfileRecord, UserRecord
from app.db.models import GoalPriceHistoryRecord
from app.db.session import get_db
from app.domain.models import (
    AllocationStrategy,
    AllocationStrategyType,
    FinancialGoal,
    GoalContribution,
)
from app.domain.planning import build_financial_plan
from app.repositories.sqlalchemy import GoalsRepository
from app.repositories.finance import FinanceRepository
from app.services.auth import delete_user_account


router = APIRouter(prefix="/api")


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    if not settings.dev_auth_fallback_enabled:
        raise HTTPException(status_code=404, detail="Endpoint is disabled")

    existing_user = db.scalar(select(UserRecord).where(UserRecord.email == payload.email))
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="User with this email already exists")

    user = UserRecord(email=payload.email)
    db.add(user)
    db.flush()
    db.add(
        UserProfileRecord(
            user_id=user.id,
            name=payload.name,
            base_currency=payload.base_currency,
        )
    )
    db.add(AllocationStrategyRecord(user_id=user.id))
    db.commit()
    return UserResponse(
        id=user.id,
        email=user.email,
        name=payload.name,
        base_currency=payload.base_currency,
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> UserResponse:
    user = db.get(UserRecord, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    profile = db.get(UserProfileRecord, user_id)
    return UserResponse(
        id=user.id,
        email=user.email,
        name=profile.name if profile else None,
        base_currency=profile.base_currency if profile else "USD",
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_required_current_user_id),
) -> None:
    delete_user_account(db, user_id)


@router.get("/goals", response_model=list[GoalResponse])
def list_goals(repo: GoalsRepository = Depends(get_repository)) -> list[FinancialGoal]:
    return repo.list_goals()


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate,
    repo: GoalsRepository = Depends(get_repository),
) -> FinancialGoal:
    goal = FinancialGoal(
        title=payload.title,
        category=payload.category,
        description=payload.description,
        target_amount=payload.target_amount,
        currency=payload.currency,
        current_amount=payload.current_amount,
        desired_date=payload.desired_date,
        priority=payload.priority,
        importance=payload.importance,
        deadline_type=payload.deadline_type,
        allocation_weight=payload.allocation_weight,
        product_url=payload.product_url,
        expected_purchase_date=payload.expected_purchase_date,
        notes=payload.notes,
    )
    return repo.add_goal(goal)


@router.get("/goals/{goal_id}", response_model=GoalResponse)
def get_goal(
    goal_id: str,
    repo: GoalsRepository = Depends(get_repository),
) -> FinancialGoal:
    goal = repo.get_goal(goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.patch("/goals/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: str,
    payload: GoalUpdate,
    repo: GoalsRepository = Depends(get_repository),
) -> FinancialGoal:
    goal = repo.update_goal(goal_id, payload.model_dump(exclude_unset=True))
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_goal(
    goal_id: str,
    repo: GoalsRepository = Depends(get_repository),
) -> None:
    if not repo.archive_goal(goal_id):
        raise HTTPException(status_code=404, detail="Goal not found")


@router.get("/goals/{goal_id}/price-history", response_model=list[GoalPriceHistoryResponse])
def list_goal_price_history(
    goal_id: str,
    repo: GoalsRepository = Depends(get_repository),
) -> list[GoalPriceHistoryRecord]:
    try:
        return repo.list_price_history(goal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/goals/{goal_id}/price-history",
    response_model=GoalPriceHistoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_goal_price_change(
    goal_id: str,
    payload: GoalPriceHistoryCreate,
    repo: GoalsRepository = Depends(get_repository),
) -> GoalPriceHistoryRecord:
    try:
        return repo.record_price_change(
            goal_id=goal_id,
            new_amount=payload.new_amount,
            currency=payload.currency,
            source=payload.source,
            note=payload.note,
            changed_at=payload.changed_at or date.today(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/goals/{goal_id}/contributions",
    response_model=ContributionResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_contribution(
    goal_id: str,
    payload: ContributionCreate,
    repo: GoalsRepository = Depends(get_repository),
) -> GoalContribution:
    goal = repo.get_goal(goal_id)
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found")

    contribution = GoalContribution(
        goal_id=goal_id,
        type=payload.type,
        amount=payload.amount,
        currency=payload.currency or goal.currency,
        source=payload.source,
        comment=payload.comment,
        occurred_at=payload.occurred_at or date.today(),
    )

    try:
        return repo.add_contribution(contribution)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/goals/{goal_id}/contributions", response_model=list[ContributionResponse])
def list_contributions(
    goal_id: str,
    repo: GoalsRepository = Depends(get_repository),
) -> list[GoalContribution]:
    if repo.get_goal(goal_id) is None:
        raise HTTPException(status_code=404, detail="Goal not found")
    return repo.list_contributions(goal_id)


@router.post("/contributions/{contribution_id}/reverse", response_model=ContributionResponse)
def reverse_contribution(
    contribution_id: str,
    repo: GoalsRepository = Depends(get_repository),
) -> GoalContribution:
    try:
        contribution = repo.reverse_contribution(contribution_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if contribution is None:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return contribution


@router.post("/priorities", response_model=list[GoalResponse])
def update_priorities(
    payload: PriorityUpdate,
    repo: GoalsRepository = Depends(get_repository),
) -> list[FinancialGoal]:
    try:
        return repo.update_priorities(payload.ordered_goal_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/plan", response_model=PlanResponse)
def get_plan(
    repo: GoalsRepository = Depends(get_repository),
    finance_repo: FinanceRepository = Depends(get_finance_repository),
) -> PlanResponse:
    settings = repo.get_plan_settings()
    summary = finance_repo.build_summary()
    return build_plan_response(summary.effective_monthly_available_amount, settings.strategy, repo)


@router.get("/plan/strategy", response_model=StrategyResponse)
def get_strategy(repo: GoalsRepository = Depends(get_repository)) -> StrategyResponse:
    strategy = repo.get_plan_settings().strategy
    return StrategyResponse(
        type=strategy.type,
        weights=strategy.weights,
        fixed_amounts=strategy.fixed_amounts,
    )


@router.post("/plan/strategy", response_model=PlanResponse)
def update_strategy(
    payload: StrategyUpdate,
    repo: GoalsRepository = Depends(get_repository),
    finance_repo: FinanceRepository = Depends(get_finance_repository),
) -> PlanResponse:
    strategy = AllocationStrategy(
        type=payload.type,
        weights=payload.weights,
        fixed_amounts=payload.fixed_amounts,
    )
    if strategy.type == AllocationStrategyType.PROPORTIONAL:
        validate_proportional_weights(strategy, repo)
    if strategy.type == AllocationStrategyType.CUSTOM:
        validate_custom_fixed_amounts(strategy, repo)
    settings = repo.update_strategy(strategy)
    summary = finance_repo.build_summary()
    return build_plan_response(summary.effective_monthly_available_amount, settings.strategy, repo)


@router.post("/plan/recalculate", response_model=PlanResponse)
def recalculate_plan(
    monthly_available_amount: Decimal | None = None,
    repo: GoalsRepository = Depends(get_repository),
    finance_repo: FinanceRepository = Depends(get_finance_repository),
) -> PlanResponse:
    settings = repo.get_plan_settings()
    summary = finance_repo.build_summary()
    amount = monthly_available_amount or summary.effective_monthly_available_amount
    return build_plan_response(amount, settings.strategy, repo)


@router.post("/scenarios/monthly-amount", response_model=ScenarioResponse)
def simulate_monthly_amount(
    payload: ScenarioRequest,
    repo: GoalsRepository = Depends(get_repository),
    finance_repo: FinanceRepository = Depends(get_finance_repository),
) -> ScenarioResponse:
    settings = repo.get_plan_settings()
    summary = finance_repo.build_summary()
    goals, currency_conflicts = repo.list_goals_for_planning_with_warnings()
    base_plan = build_financial_plan(
        goals=goals,
        monthly_available_amount=summary.effective_monthly_available_amount,
        strategy=settings.strategy,
    )
    base_plan.conflicts = [*currency_conflicts, *base_plan.conflicts]
    scenario_plan = build_financial_plan(
        goals=goals,
        monthly_available_amount=payload.monthly_available_amount,
        strategy=settings.strategy,
    )
    scenario_plan.conflicts = [*currency_conflicts, *scenario_plan.conflicts]
    return ScenarioResponse(
        scenario_name=payload.scenario_name,
        base=base_plan,
        scenario=scenario_plan,
    )


def build_plan_response(
    monthly_available_amount: Decimal,
    strategy: AllocationStrategy,
    repo: GoalsRepository,
) -> PlanResponse:
    if strategy.type == AllocationStrategyType.PROPORTIONAL:
        validate_proportional_weights(strategy, repo)
    if strategy.type == AllocationStrategyType.CUSTOM:
        validate_custom_fixed_amounts(strategy, repo)

    goals, currency_conflicts = repo.list_goals_for_planning_with_warnings()

    plan = build_financial_plan(
        goals=goals,
        monthly_available_amount=monthly_available_amount,
        strategy=strategy,
    )
    plan.conflicts = [*currency_conflicts, *plan.conflicts]
    return PlanResponse(**plan.model_dump())

def validate_proportional_weights(strategy: AllocationStrategy, repo: GoalsRepository) -> None:
    if not strategy.weights:
        return

    goal_ids = {goal.id for goal in repo.list_goals()}
    unknown_goal_ids = set(strategy.weights) - goal_ids
    if unknown_goal_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown goal ids in weights: {sorted(unknown_goal_ids)}",
        )


def validate_custom_fixed_amounts(strategy: AllocationStrategy, repo: GoalsRepository) -> None:
    if not strategy.fixed_amounts:
        return

    goal_ids = {goal.id for goal in repo.list_goals()}
    unknown_goal_ids = set(strategy.fixed_amounts) - goal_ids
    if unknown_goal_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown goal ids in fixed_amounts: {sorted(unknown_goal_ids)}",
        )

    negative_goal_ids = [
        goal_id for goal_id, amount in strategy.fixed_amounts.items() if amount < 0
    ]
    if negative_goal_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Negative fixed amounts are not allowed: {sorted(negative_goal_ids)}",
        )
