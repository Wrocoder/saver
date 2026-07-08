from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.models import (
    AllocationStrategy,
    FinancialGoal,
    GoalContribution,
    PlanSettings,
)


@dataclass(slots=True)
class InMemoryRepository:
    goals: dict[str, FinancialGoal] = field(default_factory=dict)
    contributions: dict[str, list[GoalContribution]] = field(default_factory=dict)
    settings: PlanSettings = field(
        default_factory=lambda: PlanSettings(monthly_available_amount=Decimal("300"))
    )

    def list_goals(self) -> list[FinancialGoal]:
        return sorted(self.goals.values(), key=lambda goal: goal.priority)

    def add_goal(self, goal: FinancialGoal) -> FinancialGoal:
        goal.refresh_status()
        self.goals[goal.id] = goal
        self.contributions.setdefault(goal.id, [])
        return goal

    def get_goal(self, goal_id: str) -> FinancialGoal | None:
        return self.goals.get(goal_id)

    def touch_goal(self, goal: FinancialGoal) -> None:
        goal.refresh_status()
        goal.updated_at = datetime.now(UTC)
        self.goals[goal.id] = goal

    def add_contribution(self, contribution: GoalContribution) -> GoalContribution:
        self.contributions.setdefault(contribution.goal_id, []).append(contribution)
        return contribution

    def list_contributions(self, goal_id: str) -> list[GoalContribution]:
        return sorted(
            self.contributions.get(goal_id, []),
            key=lambda contribution: contribution.occurred_at,
            reverse=True,
        )

    def update_priorities(self, ordered_goal_ids: list[str]) -> list[FinancialGoal]:
        unknown_ids = set(ordered_goal_ids) - set(self.goals)
        if unknown_ids:
            raise ValueError(f"Unknown goal ids: {sorted(unknown_ids)}")

        for position, goal_id in enumerate(ordered_goal_ids, start=1):
            goal = self.goals[goal_id]
            goal.priority = position
            self.touch_goal(goal)

        return self.list_goals()

    def get_plan_settings(self) -> PlanSettings:
        return self.settings

    def update_strategy(self, strategy: AllocationStrategy) -> PlanSettings:
        self.settings.strategy = strategy
        return self.settings

    def reset(self) -> None:
        self.goals.clear()
        self.contributions.clear()
        self.settings = PlanSettings(monthly_available_amount=Decimal("300"))


repository = InMemoryRepository()
