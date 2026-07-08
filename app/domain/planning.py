from datetime import date
from decimal import Decimal, ROUND_CEILING

from pydantic import BaseModel, Field

from app.domain.models import (
    AllocationStrategy,
    AllocationStrategyType,
    DeadlineType,
    FinancialGoal,
    GoalStatus,
)

MAX_PROJECTION_MONTHS = 600
WEEKS_IN_MONTH = Decimal("4.345")


class MonthlyAllocation(BaseModel):
    month_index: int
    period_date: date
    allocations: dict[str, Decimal]


class GoalProjection(BaseModel):
    goal_id: str
    title: str
    currency: str
    target_amount: Decimal
    current_amount: Decimal
    remaining_amount: Decimal
    progress_percent: Decimal
    allocated_first_month: Decimal
    required_monthly_amount: Decimal | None
    required_weekly_amount: Decimal | None
    expected_completion_date: date | None
    desired_date: date | None
    deviation_days: int | None
    status: str
    deadline_type: DeadlineType
    probability: str
    explanation: str


class FinancialPlanResult(BaseModel):
    monthly_available_amount: Decimal
    strategy: AllocationStrategyType
    generated_at: date = Field(default_factory=date.today)
    goals: list[GoalProjection]
    monthly_schedule: list[MonthlyAllocation]
    conflicts: list[str]
    recommendations: list[str]


def build_financial_plan(
    goals: list[FinancialGoal],
    monthly_available_amount: Decimal,
    strategy: AllocationStrategy,
    today: date | None = None,
) -> FinancialPlanResult:
    today = today or date.today()
    active_goals = [
        goal
        for goal in goals
        if goal.status in {GoalStatus.ACTIVE, GoalStatus.BEHIND, GoalStatus.REACHED}
    ]
    active_goals = sort_goals(active_goals, strategy.type)

    monthly_schedule, completion_dates = simulate_allocation(
        active_goals,
        monthly_available_amount,
        strategy,
        today,
    )

    first_month_allocations = (
        monthly_schedule[0].allocations if monthly_schedule else {}
    )

    projections = [
        build_goal_projection(
            goal=goal,
            allocated_first_month=first_month_allocations.get(goal.id, Decimal("0")),
            expected_completion_date=completion_dates.get(goal.id),
            today=today,
        )
        for goal in active_goals
    ]

    conflicts = detect_conflicts(projections, monthly_available_amount)
    recommendations = build_recommendations(projections, conflicts)

    return FinancialPlanResult(
        monthly_available_amount=monthly_available_amount,
        strategy=strategy.type,
        goals=projections,
        monthly_schedule=monthly_schedule,
        conflicts=conflicts,
        recommendations=recommendations,
    )


def simulate_allocation(
    goals: list[FinancialGoal],
    monthly_available_amount: Decimal,
    strategy: AllocationStrategy,
    today: date,
) -> tuple[list[MonthlyAllocation], dict[str, date]]:
    if monthly_available_amount <= 0:
        return [], {}

    remaining = {goal.id: goal.remaining_amount() for goal in goals}
    completion_dates = {
        goal.id: today for goal in goals if goal.remaining_amount() == 0
    }
    schedule: list[MonthlyAllocation] = []

    for month_index in range(1, MAX_PROJECTION_MONTHS + 1):
        unfinished_goals = [
            goal for goal in goals if remaining[goal.id] > 0 and goal.id not in completion_dates
        ]
        if not unfinished_goals:
            break

        allocations = allocate_period(
            unfinished_goals,
            remaining,
            monthly_available_amount,
            strategy,
        )

        if not any(amount > 0 for amount in allocations.values()):
            break

        period_date = add_months(today, month_index)

        for goal_id, amount in allocations.items():
            remaining[goal_id] = max(Decimal("0"), remaining[goal_id] - amount)
            if remaining[goal_id] == 0 and goal_id not in completion_dates:
                completion_dates[goal_id] = period_date

        schedule.append(
            MonthlyAllocation(
                month_index=month_index,
                period_date=period_date,
                allocations=allocations,
            )
        )

    return schedule, completion_dates


def allocate_period(
    goals: list[FinancialGoal],
    remaining: dict[str, Decimal],
    monthly_available_amount: Decimal,
    strategy: AllocationStrategy,
) -> dict[str, Decimal]:
    if strategy.type in {
        AllocationStrategyType.STRICT_PRIORITY,
        AllocationStrategyType.NEAREST_DEADLINE,
        AllocationStrategyType.SMALLEST_GOAL_FIRST,
    }:
        return allocate_strict(goals, remaining, monthly_available_amount)

    if strategy.type == AllocationStrategyType.PROPORTIONAL:
        return allocate_proportional(goals, remaining, monthly_available_amount, strategy)

    if strategy.type == AllocationStrategyType.CUSTOM:
        return allocate_custom(goals, remaining, monthly_available_amount, strategy)

    return allocate_strict(goals, remaining, monthly_available_amount)


def allocate_strict(
    goals: list[FinancialGoal],
    remaining: dict[str, Decimal],
    monthly_available_amount: Decimal,
) -> dict[str, Decimal]:
    available = monthly_available_amount
    allocations: dict[str, Decimal] = {}

    for goal in goals:
        if available <= 0:
            break
        amount = min(available, remaining[goal.id])
        if amount > 0:
            allocations[goal.id] = amount
            available -= amount

    return allocations


def allocate_proportional(
    goals: list[FinancialGoal],
    remaining: dict[str, Decimal],
    monthly_available_amount: Decimal,
    strategy: AllocationStrategy,
) -> dict[str, Decimal]:
    allocations = {goal.id: Decimal("0") for goal in goals}
    available = monthly_available_amount
    candidates = [goal for goal in goals if remaining[goal.id] > 0]

    while available > 0 and candidates:
        total_weight = sum(weight_for(goal, strategy) for goal in candidates)
        if total_weight <= 0:
            total_weight = Decimal(len(candidates))

        spent = Decimal("0")
        next_candidates: list[FinancialGoal] = []

        for goal in candidates:
            weight = weight_for(goal, strategy)
            if weight <= 0:
                weight = Decimal("1")

            share = available * weight / total_weight
            amount = min(share, remaining[goal.id] - allocations[goal.id])

            if amount > 0:
                allocations[goal.id] += amount
                spent += amount

            if allocations[goal.id] < remaining[goal.id]:
                next_candidates.append(goal)

        if spent <= 0:
            break

        available -= spent
        candidates = next_candidates

    return {goal_id: amount for goal_id, amount in allocations.items() if amount > 0}


def allocate_custom(
    goals: list[FinancialGoal],
    remaining: dict[str, Decimal],
    monthly_available_amount: Decimal,
    strategy: AllocationStrategy,
) -> dict[str, Decimal]:
    allocations: dict[str, Decimal] = {}
    available = monthly_available_amount

    for goal in goals:
        if available <= 0:
            break

        configured_amount = strategy.fixed_amounts.get(goal.id, Decimal("0"))
        amount = min(configured_amount, remaining[goal.id], available)
        if amount > 0:
            allocations[goal.id] = amount
            available -= amount

    return allocations


def build_goal_projection(
    goal: FinancialGoal,
    allocated_first_month: Decimal,
    expected_completion_date: date | None,
    today: date,
) -> GoalProjection:
    remaining = goal.remaining_amount()
    progress = progress_percent(goal.current_amount, goal.target_amount)
    months_left = months_until(today, goal.desired_date) if goal.desired_date else None
    required_monthly = (
        remaining / Decimal(months_left)
        if months_left and months_left > 0 and remaining > 0
        else Decimal("0")
        if remaining == 0
        else None
    )
    required_weekly = required_monthly / WEEKS_IN_MONTH if required_monthly is not None else None
    deviation_days = (
        (goal.desired_date - expected_completion_date).days
        if goal.desired_date and expected_completion_date
        else None
    )
    status = projection_status(goal, expected_completion_date, today)
    probability = probability_label(allocated_first_month, required_monthly, remaining)
    explanation = explain_projection(goal, expected_completion_date, deviation_days, status)

    return GoalProjection(
        goal_id=goal.id,
        title=goal.title,
        currency=goal.currency,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        remaining_amount=remaining,
        progress_percent=progress,
        allocated_first_month=allocated_first_month,
        required_monthly_amount=required_monthly,
        required_weekly_amount=required_weekly,
        expected_completion_date=expected_completion_date,
        desired_date=goal.desired_date,
        deviation_days=deviation_days,
        status=status,
        deadline_type=goal.deadline_type,
        probability=probability,
        explanation=explanation,
    )


def projection_status(
    goal: FinancialGoal,
    expected_completion_date: date | None,
    today: date,
) -> str:
    if goal.remaining_amount() == 0:
        return "reached"
    if expected_completion_date is None:
        return "not_funded"
    if goal.desired_date is None:
        return "on_track"
    if expected_completion_date <= goal.desired_date:
        return "ahead" if (goal.desired_date - expected_completion_date).days >= 14 else "on_track"
    if goal.deadline_type == DeadlineType.HARD:
        return "at_risk"
    return "late_but_adjustable"


def probability_label(
    allocated_first_month: Decimal,
    required_monthly: Decimal | None,
    remaining: Decimal,
) -> str:
    if remaining == 0:
        return "completed"
    if required_monthly is None or required_monthly == 0:
        return "unknown"
    ratio = allocated_first_month / required_monthly
    if ratio >= Decimal("1.10"):
        return "high"
    if ratio >= Decimal("0.80"):
        return "medium"
    return "low"


def detect_conflicts(
    projections: list[GoalProjection],
    monthly_available_amount: Decimal,
) -> list[str]:
    conflicts: list[str] = []

    if monthly_available_amount <= 0 and any(goal.remaining_amount > 0 for goal in projections):
        conflicts.append("No monthly amount is available for active goals.")

    for projection in projections:
        if projection.status == "at_risk":
            conflicts.append(
                f"Goal '{projection.title}' is at risk for its hard deadline."
            )
        elif projection.status == "not_funded":
            conflicts.append(f"Goal '{projection.title}' is not receiving funds.")

    return conflicts


def build_recommendations(
    projections: list[GoalProjection],
    conflicts: list[str],
) -> list[str]:
    recommendations: list[str] = []

    for projection in projections:
        if projection.status in {"at_risk", "late_but_adjustable"}:
            recommendations.append(
                f"Review priority, deadline, or monthly amount for '{projection.title}'."
            )
        elif projection.status == "not_funded":
            recommendations.append(
                f"Allocate at least part of the monthly amount to '{projection.title}'."
            )

    if not recommendations and not conflicts and projections:
        recommendations.append("Current plan is consistent with the entered data.")

    return recommendations


def explain_projection(
    goal: FinancialGoal,
    expected_completion_date: date | None,
    deviation_days: int | None,
    status: str,
) -> str:
    if status == "reached":
        return f"Goal '{goal.title}' has reached the target amount."
    if expected_completion_date is None:
        return f"Goal '{goal.title}' has no projected completion date with the current allocation."
    if goal.desired_date is None:
        return f"At the current pace, '{goal.title}' is projected for {expected_completion_date.isoformat()}."
    if deviation_days is not None and deviation_days >= 0:
        return (
            f"At the current pace, '{goal.title}' is projected for "
            f"{expected_completion_date.isoformat()}, {deviation_days} days before the target date."
        )
    if deviation_days is not None:
        return (
            f"At the current pace, '{goal.title}' is projected for "
            f"{expected_completion_date.isoformat()}, {abs(deviation_days)} days after the target date."
        )
    return f"At the current pace, '{goal.title}' has been recalculated."


def sort_goals(
    goals: list[FinancialGoal],
    strategy_type: AllocationStrategyType,
) -> list[FinancialGoal]:
    if strategy_type == AllocationStrategyType.NEAREST_DEADLINE:
        return sorted(goals, key=lambda goal: (goal.desired_date is None, goal.desired_date, goal.priority))
    if strategy_type == AllocationStrategyType.SMALLEST_GOAL_FIRST:
        return sorted(goals, key=lambda goal: (goal.remaining_amount(), goal.priority))
    return sorted(goals, key=lambda goal: goal.priority)


def weight_for(goal: FinancialGoal, strategy: AllocationStrategy) -> Decimal:
    if goal.id in strategy.weights:
        return strategy.weights[goal.id]
    if goal.allocation_weight is not None:
        return goal.allocation_weight
    return Decimal("1")


def progress_percent(current_amount: Decimal, target_amount: Decimal) -> Decimal:
    if target_amount <= 0:
        return Decimal("0")
    return min(Decimal("100"), current_amount / target_amount * Decimal("100"))


def months_until(today: date, target_date: date | None) -> int | None:
    if target_date is None:
        return None
    if target_date <= today:
        return 0
    days = Decimal((target_date - today).days)
    return int((days / Decimal("30.4375")).to_integral_value(rounding=ROUND_CEILING))


def add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, days_in_month(year, month))
    return date(year, month, day)


def days_in_month(year: int, month: int) -> int:
    if month == 2:
        is_leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return 29 if is_leap else 28
    if month in {4, 6, 9, 11}:
        return 30
    return 31
