from datetime import date
from decimal import Decimal

from app.domain.models import (
    AllocationStrategy,
    AllocationStrategyType,
    DeadlineType,
    FinancialGoal,
)
from app.domain.planning import build_financial_plan, build_scenario_presets


def test_single_goal_expected_completion_with_monthly_amount() -> None:
    goal = FinancialGoal(
        title="iPhone",
        target_amount=Decimal("1000"),
        current_amount=Decimal("200"),
        desired_date=date(2026, 11, 1),
    )

    plan = build_financial_plan(
        goals=[goal],
        monthly_available_amount=Decimal("300"),
        strategy=AllocationStrategy(type=AllocationStrategyType.STRICT_PRIORITY),
        today=date(2026, 7, 1),
    )

    projection = plan.goals[0]
    assert projection.remaining_amount == Decimal("800")
    assert projection.expected_completion_date == date(2026, 10, 1)
    assert projection.status == "ahead"


def test_strict_priority_rolls_money_to_next_goal_after_completion() -> None:
    phone = FinancialGoal(
        title="Phone",
        target_amount=Decimal("500"),
        current_amount=Decimal("200"),
        priority=1,
    )
    trip = FinancialGoal(
        title="Trip",
        target_amount=Decimal("600"),
        current_amount=Decimal("0"),
        priority=2,
    )

    plan = build_financial_plan(
        goals=[trip, phone],
        monthly_available_amount=Decimal("300"),
        strategy=AllocationStrategy(type=AllocationStrategyType.STRICT_PRIORITY),
        today=date(2026, 7, 1),
    )

    projections = {projection.title: projection for projection in plan.goals}
    assert projections["Phone"].expected_completion_date == date(2026, 8, 1)
    assert projections["Trip"].expected_completion_date == date(2026, 10, 1)
    assert plan.monthly_schedule[0].allocations == {phone.id: Decimal("300")}


def test_proportional_strategy_distributes_by_weights() -> None:
    car = FinancialGoal(
        title="Car",
        target_amount=Decimal("1000"),
        priority=1,
        allocation_weight=Decimal("50"),
    )
    vacation = FinancialGoal(
        title="Vacation",
        target_amount=Decimal("1000"),
        priority=2,
        allocation_weight=Decimal("30"),
    )
    phone = FinancialGoal(
        title="Phone",
        target_amount=Decimal("1000"),
        priority=3,
        allocation_weight=Decimal("20"),
    )

    plan = build_financial_plan(
        goals=[car, vacation, phone],
        monthly_available_amount=Decimal("1000"),
        strategy=AllocationStrategy(type=AllocationStrategyType.PROPORTIONAL),
        today=date(2026, 7, 1),
    )

    first_month = plan.monthly_schedule[0].allocations
    assert first_month[car.id] == Decimal("500")
    assert first_month[vacation.id] == Decimal("300")
    assert first_month[phone.id] == Decimal("200")


def test_nearest_deadline_strategy_funds_earliest_deadline_first() -> None:
    car = FinancialGoal(
        title="Car",
        target_amount=Decimal("300"),
        current_amount=Decimal("0"),
        priority=1,
    )
    tuition = FinancialGoal(
        title="Tuition",
        target_amount=Decimal("300"),
        current_amount=Decimal("0"),
        desired_date=date(2026, 8, 15),
        priority=3,
    )
    trip = FinancialGoal(
        title="Trip",
        target_amount=Decimal("300"),
        current_amount=Decimal("0"),
        desired_date=date(2026, 10, 1),
        priority=2,
    )

    plan = build_financial_plan(
        goals=[car, trip, tuition],
        monthly_available_amount=Decimal("300"),
        strategy=AllocationStrategy(type=AllocationStrategyType.NEAREST_DEADLINE),
        today=date(2026, 7, 1),
    )

    assert [projection.title for projection in plan.goals] == ["Tuition", "Trip", "Car"]
    assert plan.monthly_schedule[0].allocations == {tuition.id: Decimal("300")}
    assert plan.monthly_schedule[1].allocations == {trip.id: Decimal("300")}
    assert plan.monthly_schedule[2].allocations == {car.id: Decimal("300")}


def test_smallest_goal_first_strategy_funds_lowest_remaining_amount_first() -> None:
    car = FinancialGoal(
        title="Car",
        target_amount=Decimal("1200"),
        current_amount=Decimal("0"),
        priority=1,
    )
    phone = FinancialGoal(
        title="Phone",
        target_amount=Decimal("600"),
        current_amount=Decimal("250"),
        priority=3,
    )
    book = FinancialGoal(
        title="Book",
        target_amount=Decimal("120"),
        current_amount=Decimal("0"),
        priority=2,
    )

    plan = build_financial_plan(
        goals=[car, book, phone],
        monthly_available_amount=Decimal("300"),
        strategy=AllocationStrategy(type=AllocationStrategyType.SMALLEST_GOAL_FIRST),
        today=date(2026, 7, 1),
    )

    assert [projection.title for projection in plan.goals] == ["Book", "Phone", "Car"]
    assert plan.monthly_schedule[0].allocations == {
        book.id: Decimal("120"),
        phone.id: Decimal("180"),
    }
    assert plan.monthly_schedule[1].allocations == {phone.id: Decimal("170"), car.id: Decimal("130")}
    assert plan.monthly_schedule[2].allocations == {car.id: Decimal("300")}


def test_custom_strategy_uses_fixed_amounts_per_goal() -> None:
    emergency_fund = FinancialGoal(
        title="Emergency fund",
        target_amount=Decimal("1000"),
        current_amount=Decimal("100"),
        priority=1,
    )
    trip = FinancialGoal(
        title="Trip",
        target_amount=Decimal("800"),
        current_amount=Decimal("0"),
        priority=2,
    )

    plan = build_financial_plan(
        goals=[trip, emergency_fund],
        monthly_available_amount=Decimal("300"),
        strategy=AllocationStrategy(
            type=AllocationStrategyType.CUSTOM,
            fixed_amounts={
                emergency_fund.id: Decimal("200"),
                trip.id: Decimal("80"),
            },
        ),
        today=date(2026, 7, 1),
    )

    assert plan.monthly_schedule[0].allocations == {
        emergency_fund.id: Decimal("200"),
        trip.id: Decimal("80"),
    }
    assert plan.monthly_schedule[4].allocations == {
        emergency_fund.id: Decimal("100"),
        trip.id: Decimal("80"),
    }
    assert plan.monthly_schedule[5].allocations == {trip.id: Decimal("80")}
    projections = {projection.title: projection for projection in plan.goals}
    assert projections["Emergency fund"].expected_completion_date == date(2026, 12, 1)
    assert projections["Trip"].expected_completion_date == date(2027, 5, 1)


def test_one_time_inflow_accelerates_goal_schedule() -> None:
    phone = FinancialGoal(
        title="Phone",
        target_amount=Decimal("500"),
        current_amount=Decimal("200"),
        priority=1,
    )
    trip = FinancialGoal(
        title="Trip",
        target_amount=Decimal("400"),
        current_amount=Decimal("0"),
        priority=2,
    )

    plan = build_financial_plan(
        goals=[trip, phone],
        monthly_available_amount=Decimal("100"),
        strategy=AllocationStrategy(type=AllocationStrategyType.STRICT_PRIORITY),
        today=date(2026, 7, 1),
        one_time_inflows={2: Decimal("300")},
    )

    assert plan.monthly_schedule[0].allocations == {phone.id: Decimal("100")}
    assert plan.monthly_schedule[1].allocations == {
        phone.id: Decimal("200"),
        trip.id: Decimal("200"),
    }
    projections = {projection.title: projection for projection in plan.goals}
    assert projections["Phone"].expected_completion_date == date(2026, 9, 1)
    assert projections["Trip"].expected_completion_date == date(2026, 11, 1)


def test_one_time_inflow_can_fund_goal_without_monthly_amount() -> None:
    goal = FinancialGoal(
        title="Laptop",
        target_amount=Decimal("250"),
        current_amount=Decimal("0"),
    )

    plan = build_financial_plan(
        goals=[goal],
        monthly_available_amount=Decimal("0"),
        strategy=AllocationStrategy(type=AllocationStrategyType.STRICT_PRIORITY),
        today=date(2026, 7, 1),
        one_time_inflows={2: Decimal("250")},
    )

    projection = plan.goals[0]
    assert plan.monthly_schedule[0].month_index == 2
    assert plan.monthly_schedule[0].allocations == {goal.id: Decimal("250")}
    assert projection.allocated_first_month == Decimal("0")
    assert projection.expected_completion_date == date(2026, 9, 1)
    assert projection.status == "on_track"
    assert plan.conflicts == []


def test_skipped_months_delay_goal_schedule() -> None:
    goal = FinancialGoal(
        title="Camera",
        target_amount=Decimal("300"),
        current_amount=Decimal("0"),
    )

    plan = build_financial_plan(
        goals=[goal],
        monthly_available_amount=Decimal("100"),
        strategy=AllocationStrategy(type=AllocationStrategyType.STRICT_PRIORITY),
        today=date(2026, 7, 1),
        skipped_months={2},
    )

    assert [period.month_index for period in plan.monthly_schedule] == [1, 3, 4]
    assert all(period.allocations == {goal.id: Decimal("100")} for period in plan.monthly_schedule)
    assert plan.goals[0].allocated_first_month == Decimal("100")
    assert plan.goals[0].expected_completion_date == date(2026, 11, 1)


def test_skipping_first_month_sets_first_month_allocation_to_zero() -> None:
    goal = FinancialGoal(
        title="Course",
        target_amount=Decimal("200"),
        current_amount=Decimal("0"),
    )

    plan = build_financial_plan(
        goals=[goal],
        monthly_available_amount=Decimal("100"),
        strategy=AllocationStrategy(type=AllocationStrategyType.STRICT_PRIORITY),
        today=date(2026, 7, 1),
        skipped_months={1},
    )

    assert [period.month_index for period in plan.monthly_schedule] == [2, 3]
    assert plan.goals[0].allocated_first_month == Decimal("0")
    assert plan.goals[0].expected_completion_date == date(2026, 10, 1)
    assert plan.goals[0].status == "on_track"


def test_scenario_presets_create_cautious_realistic_and_optimistic_plans() -> None:
    goal = FinancialGoal(
        title="Bike",
        target_amount=Decimal("1000"),
        current_amount=Decimal("0"),
    )

    presets = build_scenario_presets(
        goals=[goal],
        monthly_available_amount=Decimal("100"),
        strategy=AllocationStrategy(type=AllocationStrategyType.STRICT_PRIORITY),
        today=date(2026, 7, 1),
    )

    assert [preset.name for preset in presets] == ["cautious", "realistic", "optimistic"]
    assert [preset.monthly_available_amount for preset in presets] == [
        Decimal("80.00"),
        Decimal("100.00"),
        Decimal("120.00"),
    ]
    cautious, realistic, optimistic = presets
    assert cautious.skipped_months == [4, 8, 12]
    assert cautious.plan.monthly_schedule[3].month_index == 5
    assert realistic.skipped_months == []
    assert optimistic.skipped_months == []
    assert cautious.plan.goals[0].expected_completion_date > realistic.plan.goals[0].expected_completion_date
    assert optimistic.plan.goals[0].expected_completion_date < realistic.plan.goals[0].expected_completion_date


def test_hard_deadline_is_marked_at_risk_when_projection_is_late() -> None:
    goal = FinancialGoal(
        title="Tuition",
        target_amount=Decimal("1000"),
        current_amount=Decimal("0"),
        desired_date=date(2026, 9, 1),
        deadline_type=DeadlineType.HARD,
    )

    plan = build_financial_plan(
        goals=[goal],
        monthly_available_amount=Decimal("300"),
        strategy=AllocationStrategy(type=AllocationStrategyType.STRICT_PRIORITY),
        today=date(2026, 7, 1),
    )

    assert plan.goals[0].status == "at_risk"
    assert "hard deadline" in plan.conflicts[0]


def test_zero_monthly_amount_marks_goal_as_not_funded() -> None:
    goal = FinancialGoal(title="Laptop", target_amount=Decimal("1000"))

    plan = build_financial_plan(
        goals=[goal],
        monthly_available_amount=Decimal("0"),
        strategy=AllocationStrategy(type=AllocationStrategyType.STRICT_PRIORITY),
        today=date(2026, 7, 1),
    )

    projection = plan.goals[0]
    assert projection.status == "not_funded"
    assert projection.allocated_first_month == Decimal("0")
    assert projection.expected_completion_date is None
    assert projection.probability == "unknown"
    assert plan.monthly_schedule == []
    assert plan.conflicts == [
        "No monthly amount is available for active goals.",
        "Goal 'Laptop' is not receiving funds.",
    ]
    assert plan.recommendations == [
        "Allocate at least part of the monthly amount to 'Laptop'."
    ]


def test_reached_goal_is_completed_without_consuming_future_allocations() -> None:
    emergency_fund = FinancialGoal(
        title="Emergency fund",
        target_amount=Decimal("1000"),
        current_amount=Decimal("1200"),
        priority=1,
    )
    trip = FinancialGoal(
        title="Trip",
        target_amount=Decimal("600"),
        current_amount=Decimal("0"),
        priority=2,
    )

    plan = build_financial_plan(
        goals=[trip, emergency_fund],
        monthly_available_amount=Decimal("300"),
        strategy=AllocationStrategy(type=AllocationStrategyType.STRICT_PRIORITY),
        today=date(2026, 7, 1),
    )

    projections = {projection.title: projection for projection in plan.goals}
    assert projections["Emergency fund"].remaining_amount == Decimal("0")
    assert projections["Emergency fund"].progress_percent == Decimal("100")
    assert projections["Emergency fund"].status == "reached"
    assert projections["Emergency fund"].probability == "completed"
    assert projections["Emergency fund"].expected_completion_date == date(2026, 7, 1)
    assert projections["Emergency fund"].allocated_first_month == Decimal("0")

    assert projections["Trip"].expected_completion_date == date(2026, 9, 1)
    assert plan.monthly_schedule[0].allocations == {trip.id: Decimal("300")}
    assert emergency_fund.id not in plan.monthly_schedule[0].allocations


def test_overdue_hard_deadline_is_reported_as_at_risk() -> None:
    goal = FinancialGoal(
        title="Tax bill",
        target_amount=Decimal("900"),
        current_amount=Decimal("0"),
        desired_date=date(2026, 6, 1),
        deadline_type=DeadlineType.HARD,
    )

    plan = build_financial_plan(
        goals=[goal],
        monthly_available_amount=Decimal("300"),
        strategy=AllocationStrategy(type=AllocationStrategyType.STRICT_PRIORITY),
        today=date(2026, 7, 1),
    )

    projection = plan.goals[0]
    assert projection.status == "at_risk"
    assert projection.required_monthly_amount is None
    assert projection.required_weekly_amount is None
    assert projection.expected_completion_date == date(2026, 10, 1)
    assert projection.deviation_days == -122
    assert projection.probability == "unknown"
    assert "122 days after the target date" in projection.explanation
    assert plan.conflicts == ["Goal 'Tax bill' is at risk for its hard deadline."]
    assert plan.recommendations == [
        "Review priority, deadline, or monthly amount for 'Tax bill'."
    ]
