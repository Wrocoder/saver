from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4


class GoalStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    BEHIND = "behind"
    REACHED = "reached"
    PURCHASED = "purchased"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class DeadlineType(StrEnum):
    HARD = "hard"
    FLEXIBLE = "flexible"


class ContributionType(StrEnum):
    ADD = "add"
    SUBTRACT = "subtract"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    ADJUSTMENT = "adjustment"


class AllocationStrategyType(StrEnum):
    STRICT_PRIORITY = "strict_priority"
    PROPORTIONAL = "proportional"
    NEAREST_DEADLINE = "nearest_deadline"
    SMALLEST_GOAL_FIRST = "smallest_goal_first"
    CUSTOM = "custom"


@dataclass(slots=True)
class FinancialGoal:
    title: str
    target_amount: Decimal
    currency: str = "USD"
    current_amount: Decimal = Decimal("0")
    desired_date: date | None = None
    priority: int = 1
    category: str | None = None
    description: str | None = None
    importance: int = 3
    deadline_type: DeadlineType = DeadlineType.FLEXIBLE
    status: GoalStatus = GoalStatus.ACTIVE
    allocation_weight: Decimal | None = None
    product_url: str | None = None
    expected_purchase_date: date | None = None
    notes: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def remaining_amount(self) -> Decimal:
        return max(Decimal("0"), self.target_amount - self.current_amount)

    def refresh_status(self) -> None:
        if self.current_amount >= self.target_amount and self.status == GoalStatus.ACTIVE:
            self.status = GoalStatus.REACHED
        elif self.current_amount < self.target_amount and self.status == GoalStatus.REACHED:
            self.status = GoalStatus.ACTIVE
        self.updated_at = datetime.now(UTC)


@dataclass(slots=True)
class GoalContribution:
    goal_id: str
    type: ContributionType
    amount: Decimal
    currency: str
    exchange_rate_id: str | None = None
    exchange_rate: Decimal | None = None
    amount_in_goal_currency: Decimal | None = None
    amount_in_base_currency: Decimal | None = None
    source: str | None = None
    comment: str | None = None
    occurred_at: date = field(default_factory=date.today)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reversed_at: datetime | None = None


@dataclass(slots=True)
class AllocationStrategy:
    type: AllocationStrategyType = AllocationStrategyType.STRICT_PRIORITY
    weights: dict[str, Decimal] = field(default_factory=dict)
    fixed_amounts: dict[str, Decimal] = field(default_factory=dict)


@dataclass(slots=True)
class PlanSettings:
    monthly_available_amount: Decimal = Decimal("300")
    strategy: AllocationStrategy = field(default_factory=AllocationStrategy)
