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


class ProjectionFactor(BaseModel):
    key: str
    label: str
    value: str
    impact: str


class ProjectionExplainability(BaseModel):
    factors: list[ProjectionFactor]
    assumptions: list[str]


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
    explainability: ProjectionExplainability


class FinancialPlanResult(BaseModel):
    monthly_available_amount: Decimal
    strategy: AllocationStrategyType
    generated_at: date = Field(default_factory=date.today)
    goals: list[GoalProjection]
    monthly_schedule: list[MonthlyAllocation]
    conflicts: list[str]
    recommendations: list[str]


class ScenarioPresetPlan(BaseModel):
    name: str
    label: str
    description: str
    assumptions: list[str]
    monthly_available_amount: Decimal
    skipped_months: list[int]
    plan: FinancialPlanResult


def build_financial_plan(
    goals: list[FinancialGoal],
    monthly_available_amount: Decimal,
    strategy: AllocationStrategy,
    today: date | None = None,
    one_time_inflows: dict[int, Decimal] | None = None,
    skipped_months: set[int] | None = None,
    scenario_completion_dates: dict[str, list[date | None]] | None = None,
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
        one_time_inflows=one_time_inflows,
        skipped_months=skipped_months,
    )

    first_month = next((period for period in monthly_schedule if period.month_index == 1), None)
    first_month_allocations = first_month.allocations if first_month else {}

    projections = [
        build_goal_projection(
            goal=goal,
            allocated_first_month=first_month_allocations.get(goal.id, Decimal("0")),
            expected_completion_date=completion_dates.get(goal.id),
            today=today,
            monthly_available_amount=monthly_available_amount,
            strategy_type=strategy.type,
            scenario_completion_dates=(
                scenario_completion_dates.get(goal.id)
                if scenario_completion_dates is not None
                else None
            ),
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


def build_financial_plan_with_scenario_probability(
    goals: list[FinancialGoal],
    monthly_available_amount: Decimal,
    strategy: AllocationStrategy,
    today: date | None = None,
    one_time_inflows: dict[int, Decimal] | None = None,
    skipped_months: set[int] | None = None,
) -> FinancialPlanResult:
    today = today or date.today()
    presets = build_scenario_presets(
        goals=goals,
        monthly_available_amount=monthly_available_amount,
        strategy=strategy,
        today=today,
        one_time_inflows=one_time_inflows,
        skipped_months=skipped_months,
    )
    return build_financial_plan(
        goals=goals,
        monthly_available_amount=monthly_available_amount,
        strategy=strategy,
        today=today,
        one_time_inflows=one_time_inflows,
        skipped_months=skipped_months,
        scenario_completion_dates=completion_dates_by_goal(presets),
    )


def build_scenario_presets(
    goals: list[FinancialGoal],
    monthly_available_amount: Decimal,
    strategy: AllocationStrategy,
    today: date | None = None,
    one_time_inflows: dict[int, Decimal] | None = None,
    skipped_months: set[int] | None = None,
) -> list[ScenarioPresetPlan]:
    today = today or date.today()
    configs = [
        {
            "name": "cautious",
            "label": "Cautious",
            "description": "Lower capacity with several missed contribution months.",
            "multiplier": Decimal("0.80"),
            "skipped_months": [4, 8, 12],
            "assumptions": [
                "Monthly savings capacity is reduced to 80% of the current plan.",
                "Regular funding is skipped in months 4, 8, and 12.",
            ],
        },
        {
            "name": "realistic",
            "label": "Realistic",
            "description": "Current plan without additional shocks or bonuses.",
            "multiplier": Decimal("1.00"),
            "skipped_months": [],
            "assumptions": [
                "Current effective monthly savings capacity is used.",
                "No extra skipped months or one-time inflows are applied.",
            ],
        },
        {
            "name": "optimistic",
            "label": "Optimistic",
            "description": "Higher capacity if income or savings discipline improves.",
            "multiplier": Decimal("1.20"),
            "skipped_months": [],
            "assumptions": [
                "Monthly savings capacity is increased to 120% of the current plan.",
                "No skipped contribution months are applied.",
            ],
        },
    ]

    presets: list[ScenarioPresetPlan] = []
    for config in configs:
        amount = scale_monthly_amount(monthly_available_amount, config["multiplier"])
        preset_skipped_months = sorted(
            {
                *set(skipped_months or set()),
                *set(config["skipped_months"]),
            }
        )
        plan = build_financial_plan(
            goals=goals,
            monthly_available_amount=amount,
            strategy=strategy,
            today=today,
            one_time_inflows=one_time_inflows,
            skipped_months=set(preset_skipped_months),
        )
        presets.append(
            ScenarioPresetPlan(
                name=str(config["name"]),
                label=str(config["label"]),
                description=str(config["description"]),
                assumptions=list(config["assumptions"]),
                monthly_available_amount=amount,
                skipped_months=preset_skipped_months,
                plan=plan,
            )
        )

    return presets


def completion_dates_by_goal(
    presets: list[ScenarioPresetPlan],
) -> dict[str, list[date | None]]:
    results: dict[str, list[date | None]] = {}
    for preset in presets:
        for goal in preset.plan.goals:
            results.setdefault(goal.goal_id, []).append(goal.expected_completion_date)
    return results


def scale_monthly_amount(monthly_available_amount: Decimal, multiplier: Decimal) -> Decimal:
    return (monthly_available_amount * multiplier).quantize(Decimal("0.01"))


def simulate_allocation(
    goals: list[FinancialGoal],
    monthly_available_amount: Decimal,
    strategy: AllocationStrategy,
    today: date,
    one_time_inflows: dict[int, Decimal] | None = None,
    skipped_months: set[int] | None = None,
) -> tuple[list[MonthlyAllocation], dict[str, date]]:
    positive_one_time_inflows = {
        month_index: amount
        for month_index, amount in (one_time_inflows or {}).items()
        if month_index >= 1 and amount > 0
    }
    normalized_skipped_months = {
        month_index
        for month_index in (skipped_months or set())
        if month_index >= 1
    }
    if monthly_available_amount <= 0 and not positive_one_time_inflows:
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

        recurring_amount = (
            Decimal("0")
            if month_index in normalized_skipped_months
            else monthly_available_amount
        )
        available_amount = recurring_amount + positive_one_time_inflows.get(month_index, Decimal("0"))
        if available_amount <= 0:
            if has_future_funding(
                month_index,
                monthly_available_amount,
                positive_one_time_inflows,
                normalized_skipped_months,
            ):
                continue
            break

        allocations = allocate_period(
            unfinished_goals,
            remaining,
            available_amount,
            strategy,
        )

        if not any(amount > 0 for amount in allocations.values()):
            if has_future_funding(
                month_index,
                monthly_available_amount,
                positive_one_time_inflows,
                normalized_skipped_months,
            ):
                continue
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


def has_future_funding(
    month_index: int,
    monthly_available_amount: Decimal,
    one_time_inflows: dict[int, Decimal],
    skipped_months: set[int],
) -> bool:
    has_future_recurring_funding = (
        monthly_available_amount > 0
        and any(
            future_month not in skipped_months
            for future_month in range(month_index + 1, MAX_PROJECTION_MONTHS + 1)
        )
    )
    has_future_one_time_funding = any(
        future_month > month_index and amount > 0
        for future_month, amount in one_time_inflows.items()
    )
    return has_future_recurring_funding or has_future_one_time_funding


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
    monthly_available_amount: Decimal,
    strategy_type: AllocationStrategyType,
    scenario_completion_dates: list[date | None] | None = None,
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
    probability = scenario_probability_label(goal, scenario_completion_dates)
    if probability is None:
        probability = probability_label(allocated_first_month, required_monthly, remaining)
    explanation = explain_projection(goal, expected_completion_date, deviation_days, status)
    explainability = build_projection_explainability(
        goal=goal,
        remaining=remaining,
        allocated_first_month=allocated_first_month,
        required_monthly=required_monthly,
        expected_completion_date=expected_completion_date,
        monthly_available_amount=monthly_available_amount,
        strategy_type=strategy_type,
        probability=probability,
        scenario_completion_dates=scenario_completion_dates,
    )

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
        explainability=explainability,
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


def scenario_probability_label(
    goal: FinancialGoal,
    scenario_completion_dates: list[date | None] | None,
) -> str | None:
    if scenario_completion_dates is None:
        return None
    if goal.remaining_amount() == 0:
        return "completed"
    if not goal.desired_date:
        return "unknown"

    successful_scenarios = sum(
        1
        for completion_date in scenario_completion_dates
        if completion_date is not None and completion_date <= goal.desired_date
    )
    scenario_count = len(scenario_completion_dates)
    if scenario_count == 0:
        return "unknown"
    if successful_scenarios == scenario_count:
        return "high"
    if successful_scenarios >= 2:
        return "medium"
    return "low"


def build_projection_explainability(
    goal: FinancialGoal,
    remaining: Decimal,
    allocated_first_month: Decimal,
    required_monthly: Decimal | None,
    expected_completion_date: date | None,
    monthly_available_amount: Decimal,
    strategy_type: AllocationStrategyType,
    probability: str,
    scenario_completion_dates: list[date | None] | None,
) -> ProjectionExplainability:
    factors = [
        ProjectionFactor(
            key="target_amount",
            label="Target amount",
            value=format_decimal(goal.target_amount),
            impact="Sets the total amount that must be funded.",
        ),
        ProjectionFactor(
            key="current_amount",
            label="Current amount",
            value=format_decimal(goal.current_amount),
            impact="Reduces the amount still needed.",
        ),
        ProjectionFactor(
            key="remaining_amount",
            label="Remaining amount",
            value=format_decimal(remaining),
            impact="Drives how many allocation periods are needed.",
        ),
        ProjectionFactor(
            key="monthly_available_amount",
            label="Monthly available amount",
            value=format_decimal(monthly_available_amount),
            impact="Caps how much can be distributed across active goals each month.",
        ),
        ProjectionFactor(
            key="allocation_strategy",
            label="Allocation strategy",
            value=strategy_type.value,
            impact="Controls how the monthly amount is split between goals.",
        ),
        ProjectionFactor(
            key="priority",
            label="Priority",
            value=str(goal.priority),
            impact="Affects funding order for priority-based strategies.",
        ),
        ProjectionFactor(
            key="first_month_allocation",
            label="First month allocation",
            value=format_decimal(allocated_first_month),
            impact="Shows the current plan's immediate funding for this goal.",
        ),
        ProjectionFactor(
            key="desired_date",
            label="Desired date",
            value=goal.desired_date.isoformat() if goal.desired_date else "not set",
            impact=(
                "Used for deadline status and scenario probability."
                if goal.desired_date
                else "No deadline is set, so deadline probability remains unknown."
            ),
        ),
        ProjectionFactor(
            key="deadline_type",
            label="Deadline type",
            value=goal.deadline_type.value,
            impact="Controls whether a late projection is marked at risk or adjustable.",
        ),
        ProjectionFactor(
            key="required_monthly_amount",
            label="Required monthly amount",
            value=format_decimal(required_monthly) if required_monthly is not None else "not available",
            impact="Compares the required pace with the projected funding pace.",
        ),
        ProjectionFactor(
            key="expected_completion_date",
            label="Projected date",
            value=expected_completion_date.isoformat() if expected_completion_date else "not projected",
            impact="Result after applying strategy, current progress, and available funding.",
        ),
        ProjectionFactor(
            key="scenario_probability",
            label="Scenario probability",
            value=probability,
            impact=scenario_probability_impact(goal, scenario_completion_dates),
        ),
    ]

    assumptions = [
        "Projection uses monthly allocation periods.",
        "Goal amounts are evaluated in the goal currency after repository-level conversion when needed.",
        "Scenario probability compares cautious, realistic, and optimistic preset completion dates against the desired date.",
    ]
    if scenario_completion_dates is None:
        assumptions[-1] = "Fallback probability compares first-month allocation with required monthly funding."

    return ProjectionExplainability(factors=factors, assumptions=assumptions)


def scenario_probability_impact(
    goal: FinancialGoal,
    scenario_completion_dates: list[date | None] | None,
) -> str:
    if scenario_completion_dates is None:
        return "Uses the simple first-month pace because scenario outcomes were not provided."
    if not goal.desired_date:
        return "No desired date is set, so scenario outcomes cannot be judged against a deadline."

    successful_scenarios = sum(
        1
        for completion_date in scenario_completion_dates
        if completion_date is not None and completion_date <= goal.desired_date
    )
    return (
        f"{successful_scenarios} of {len(scenario_completion_dates)} preset scenarios "
        "reach this goal by the desired date."
    )


def format_decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")


def detect_conflicts(
    projections: list[GoalProjection],
    monthly_available_amount: Decimal,
) -> list[str]:
    conflicts: list[str] = []

    if monthly_available_amount <= 0 and any(
        goal.remaining_amount > 0 and goal.expected_completion_date is None for goal in projections
    ):
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
