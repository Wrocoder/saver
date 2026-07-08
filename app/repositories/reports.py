from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import FinancialGoalRecord, GoalContributionRecord
from app.domain.models import AllocationStrategy, ContributionType
from app.domain.planning import build_financial_plan, progress_percent
from app.repositories.currency import CurrencyRepository, MissingExchangeRateError
from app.repositories.finance import FinanceRepository
from app.repositories.sqlalchemy import GoalsRepository


class MonthlyReportsRepository:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id
        self.currency_repo = CurrencyRepository(db)
        self.goals_repo = GoalsRepository(db, user_id)
        self.finance_repo = FinanceRepository(db, user_id)

    def build_monthly_report(self, year: int, month: int) -> dict[str, Any]:
        start, end = month_bounds(year, month)
        summary = self.finance_repo.build_summary()
        contributions = self.list_contributions(start, end)
        goals = self.goal_records_by_id()

        totals = Totals()
        goal_rows: dict[str, GoalReportAccumulator] = {}
        missing_rates: set[str] = set()

        for contribution in contributions:
            if contribution.reversed_at is not None:
                totals.reversed_count += 1
                continue

            base_amount = amount_in_base(contribution, summary.base_currency, self.currency_repo, missing_rates)
            goal_amount = contribution.amount_in_goal_currency or contribution.amount
            direction = contribution_direction(contribution.type)
            if direction > 0:
                totals.added += base_amount
            elif direction < 0:
                totals.removed += base_amount

            accumulator = goal_rows.setdefault(
                contribution.goal_id,
                GoalReportAccumulator(goal_id=contribution.goal_id),
            )
            accumulator.contributions_count += 1
            if direction > 0:
                accumulator.added += goal_amount
            elif direction < 0:
                accumulator.removed += goal_amount

        plan = self.safe_plan(summary.effective_monthly_available_amount)
        recommendations = list(plan.recommendations)
        recommendations.extend(report_recommendations(totals.net(), summary.effective_monthly_available_amount))

        return {
            "period_start": start,
            "period_end": end,
            "base_currency": summary.base_currency,
            "total_added": totals.added,
            "total_removed": totals.removed,
            "net_saved": totals.net(),
            "contributions_count": sum(row.contributions_count for row in goal_rows.values()),
            "reversed_contributions_count": totals.reversed_count,
            "safe_monthly_capacity": summary.effective_monthly_available_amount,
            "goal_reports": [
                row.to_response(goals.get(goal_id))
                for goal_id, row in sorted(goal_rows.items(), key=lambda item: goal_sort_key(goals.get(item[0])))
            ],
            "plan_recommendations": recommendations,
            "plan_conflicts": plan.conflicts,
            "warnings": [*summary.warnings, *missing_rate_warnings(missing_rates)],
        }

    def list_contributions(self, start: date, end: date) -> list[GoalContributionRecord]:
        return list(
            self.db.scalars(
                select(GoalContributionRecord)
                .where(
                    GoalContributionRecord.user_id == self.user_id,
                    GoalContributionRecord.occurred_at >= start,
                    GoalContributionRecord.occurred_at < end,
                )
                .order_by(GoalContributionRecord.occurred_at.asc(), GoalContributionRecord.created_at.asc())
            )
        )

    def goal_records_by_id(self) -> dict[str, FinancialGoalRecord]:
        records = self.db.scalars(
            select(FinancialGoalRecord).where(FinancialGoalRecord.user_id == self.user_id)
        )
        return {record.id: record for record in records}

    def safe_plan(self, monthly_available_amount: Decimal):
        goals, currency_conflicts = self.goals_repo.list_goals_for_planning_with_warnings()
        settings = self.goals_repo.get_plan_settings()
        strategy = AllocationStrategy(
            type=settings.strategy.type,
            weights=settings.strategy.weights,
            fixed_amounts=settings.strategy.fixed_amounts,
        )
        plan = build_financial_plan(
            goals=goals,
            monthly_available_amount=monthly_available_amount,
            strategy=strategy,
        )
        plan.conflicts = [*currency_conflicts, *plan.conflicts]
        return plan


class Totals:
    def __init__(self) -> None:
        self.added = Decimal("0")
        self.removed = Decimal("0")
        self.reversed_count = 0

    def net(self) -> Decimal:
        return self.added - self.removed


class GoalReportAccumulator:
    def __init__(self, goal_id: str) -> None:
        self.goal_id = goal_id
        self.added = Decimal("0")
        self.removed = Decimal("0")
        self.contributions_count = 0

    def to_response(self, goal: FinancialGoalRecord | None) -> dict[str, Any]:
        target_amount = goal.target_amount if goal is not None else Decimal("0")
        current_amount = goal.current_amount if goal is not None else Decimal("0")
        return {
            "goal_id": self.goal_id,
            "title": goal.title if goal is not None else "Archived goal",
            "currency": goal.currency if goal is not None else "",
            "added_amount": self.added,
            "removed_amount": self.removed,
            "net_amount": self.added - self.removed,
            "contributions_count": self.contributions_count,
            "current_amount": current_amount,
            "target_amount": target_amount,
            "progress_percent": progress_percent(current_amount, target_amount) if target_amount > 0 else Decimal("0"),
            "status": goal.status if goal is not None else "archived",
        }


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        return start, date(year + 1, 1, 1)
    return start, date(year, month + 1, 1)


def contribution_direction(contribution_type: str) -> int:
    if contribution_type in {ContributionType.ADD.value, ContributionType.TRANSFER_IN.value}:
        return 1
    if contribution_type in {ContributionType.SUBTRACT.value, ContributionType.TRANSFER_OUT.value}:
        return -1
    return 0


def amount_in_base(
    contribution: GoalContributionRecord,
    base_currency: str,
    currency_repo: CurrencyRepository,
    missing_rates: set[str],
) -> Decimal:
    if contribution.amount_in_base_currency is not None:
        return contribution.amount_in_base_currency
    try:
        return currency_repo.convert(contribution.amount, contribution.currency, base_currency).amount
    except MissingExchangeRateError:
        missing_rates.add(f"{contribution.currency}->{base_currency}")
        return Decimal("0")


def report_recommendations(net_saved: Decimal, safe_capacity: Decimal) -> list[str]:
    if safe_capacity <= 0:
        return ["No safe monthly savings capacity is currently available."]
    if net_saved <= 0:
        return ["No positive savings progress was recorded in this month."]
    if net_saved < safe_capacity:
        gap = safe_capacity - net_saved
        return [f"You saved {gap} less than the current safe monthly capacity."]
    if net_saved > safe_capacity:
        return ["This month exceeded the current safe savings capacity; verify that reserve assumptions still hold."]
    return ["This month matched the current safe monthly savings capacity."]


def missing_rate_warnings(missing_rates: set[str]) -> list[str]:
    if not missing_rates:
        return []
    return ["Missing exchange rates in report: " + ", ".join(sorted(missing_rates))]


def goal_sort_key(goal: FinancialGoalRecord | None) -> tuple[int, str]:
    if goal is None:
        return (9999, "")
    return (goal.priority, goal.title)
