from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AllocationStrategyRecord,
    AuditLogRecord,
    FinancialGoalRecord,
    GoalContributionRecord,
    GoalPriceHistoryRecord,
    UserProfileRecord,
)
from app.domain.models import (
    AllocationStrategy,
    AllocationStrategyType,
    ContributionType,
    DeadlineType,
    FinancialGoal,
    GoalContribution,
    GoalStatus,
    PlanSettings,
)
from app.repositories.currency import CurrencyRepository, MissingExchangeRateError


HIDDEN_GOAL_STATUSES = [GoalStatus.ARCHIVED.value, GoalStatus.CANCELLED.value]


class GoalsRepository:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id
        self.currency_repo = CurrencyRepository(db)

    def list_goals(self) -> list[FinancialGoal]:
        records = self.db.scalars(
            select(FinancialGoalRecord)
            .where(
                FinancialGoalRecord.user_id == self.user_id,
                ~FinancialGoalRecord.status.in_(HIDDEN_GOAL_STATUSES),
            )
            .order_by(FinancialGoalRecord.priority.asc(), FinancialGoalRecord.created_at.asc())
        ).all()
        return [goal_to_domain(record) for record in records]

    def list_goals_for_planning(self) -> list[FinancialGoal]:
        goals, _ = self.list_goals_for_planning_with_warnings()
        return goals

    def list_goals_for_planning_with_warnings(self) -> tuple[list[FinancialGoal], list[str]]:
        profile = self.get_or_create_profile()
        base_currency = profile.base_currency
        converted_goals: list[FinancialGoal] = []
        warnings: list[str] = []

        for goal in self.list_goals():
            try:
                target_amount = self.currency_repo.convert(
                    goal.target_amount,
                    goal.currency,
                    base_currency,
                ).amount
                current_amount = self.currency_repo.convert(
                    goal.current_amount,
                    goal.currency,
                    base_currency,
                ).amount
            except MissingExchangeRateError as exc:
                warnings.append(
                    f'Goal "{goal.title}" is excluded from projections until this rate is added: {exc}.'
                )
                continue

            converted_goals.append(
                FinancialGoal(
                    id=goal.id,
                    title=goal.title,
                    category=goal.category,
                    description=goal.description,
                    target_amount=target_amount,
                    currency=base_currency,
                    current_amount=current_amount,
                    desired_date=goal.desired_date,
                    priority=goal.priority,
                    importance=goal.importance,
                    deadline_type=goal.deadline_type,
                    status=goal.status,
                    allocation_weight=goal.allocation_weight,
                    product_url=goal.product_url,
                    expected_purchase_date=goal.expected_purchase_date,
                    notes=goal.notes,
                    created_at=goal.created_at,
                    updated_at=goal.updated_at,
                )
            )

        return converted_goals, warnings

    def add_goal(self, goal: FinancialGoal) -> FinancialGoal:
        record = FinancialGoalRecord(
            id=goal.id,
            user_id=self.user_id,
            title=goal.title,
            category=goal.category,
            description=goal.description,
            target_amount=goal.target_amount,
            currency=goal.currency,
            current_amount=goal.current_amount,
            desired_date=goal.desired_date,
            priority=goal.priority,
            importance=goal.importance,
            deadline_type=goal.deadline_type.value,
            status=goal.status.value,
            allocation_weight=goal.allocation_weight,
            product_url=goal.product_url,
            expected_purchase_date=goal.expected_purchase_date,
            notes=goal.notes,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )
        refresh_record_status(record)
        self.db.add(record)
        self.db.flush()
        self.audit("financial_goal", record.id, "create", None, goal_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return goal_to_domain(record)

    def get_goal(self, goal_id: str) -> FinancialGoal | None:
        record = self.get_goal_record(goal_id)
        return goal_to_domain(record) if record is not None else None

    def update_goal(self, goal_id: str, updates: dict[str, Any]) -> FinancialGoal | None:
        record = self.get_goal_record(goal_id)
        if record is None:
            return None

        before = goal_snapshot(record)
        previous_target_amount = record.target_amount
        for key, value in updates.items():
            if key in {"deadline_type", "status"} and value is not None:
                setattr(record, key, value.value)
            else:
                setattr(record, key, value)

        refresh_record_status(record)
        if "target_amount" in updates and record.target_amount != previous_target_amount:
            price_record = GoalPriceHistoryRecord(
                user_id=self.user_id,
                goal_id=record.id,
                previous_amount=previous_target_amount,
                new_amount=record.target_amount,
                currency=record.currency,
                source="goal_update",
                note="Updated through goal edit",
                changed_at=date.today(),
            )
            self.db.add(price_record)
            self.db.flush()
            self.audit("goal_price_history", price_record.id, "create", None, price_snapshot(price_record))
        self.audit("financial_goal", record.id, "update", before, goal_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return goal_to_domain(record)

    def archive_goal(self, goal_id: str) -> bool:
        record = self.get_goal_record(goal_id, include_hidden=True)
        if record is None or record.status in HIDDEN_GOAL_STATUSES:
            return False

        before = goal_snapshot(record)
        record.status = GoalStatus.ARCHIVED.value
        self.audit("financial_goal", record.id, "archive", before, goal_snapshot(record))
        self.db.commit()
        return True

    def list_price_history(self, goal_id: str) -> list[GoalPriceHistoryRecord]:
        if self.get_goal_record(goal_id) is None:
            raise ValueError("Goal not found")

        return list(
            self.db.scalars(
                select(GoalPriceHistoryRecord)
                .where(
                    GoalPriceHistoryRecord.user_id == self.user_id,
                    GoalPriceHistoryRecord.goal_id == goal_id,
                )
                .order_by(GoalPriceHistoryRecord.changed_at.desc(), GoalPriceHistoryRecord.created_at.desc())
            )
        )

    def record_price_change(
        self,
        goal_id: str,
        new_amount: Decimal,
        currency: str | None,
        source: str | None,
        note: str | None,
        changed_at: date,
    ) -> GoalPriceHistoryRecord:
        record = self.get_goal_record(goal_id)
        if record is None:
            raise ValueError("Goal not found")

        before_goal = goal_snapshot(record)
        price_record = GoalPriceHistoryRecord(
            user_id=self.user_id,
            goal_id=goal_id,
            previous_amount=record.target_amount,
            new_amount=new_amount,
            currency=currency or record.currency,
            source=source,
            note=note,
            changed_at=changed_at,
        )
        self.db.add(price_record)
        self.db.flush()

        record.target_amount = new_amount
        if currency is not None:
            record.currency = currency
        refresh_record_status(record)

        self.audit("goal_price_history", price_record.id, "create", None, price_snapshot(price_record))
        self.audit("financial_goal", record.id, "price_update", before_goal, goal_snapshot(record))
        self.db.commit()
        self.db.refresh(price_record)
        return price_record

    def add_contribution(self, contribution: GoalContribution) -> GoalContribution:
        goal = self.get_goal_record(contribution.goal_id)
        if goal is None:
            raise ValueError("Goal not found")

        before = goal_snapshot(goal)
        profile = self.get_or_create_profile()
        try:
            goal_conversion = self.currency_repo.convert(
                contribution.amount,
                contribution.currency,
                goal.currency,
            )
            base_conversion = self.currency_repo.convert(
                contribution.amount,
                contribution.currency,
                profile.base_currency,
            )
        except MissingExchangeRateError as exc:
            raise ValueError(str(exc)) from exc

        record = GoalContributionRecord(
            id=contribution.id,
            goal_id=contribution.goal_id,
            user_id=self.user_id,
            type=contribution.type.value,
            amount=contribution.amount,
            currency=contribution.currency,
            exchange_rate_id=goal_conversion.exchange_rate_id or base_conversion.exchange_rate_id,
            exchange_rate=goal_conversion.rate,
            amount_in_goal_currency=goal_conversion.amount,
            amount_in_base_currency=base_conversion.amount,
            source=contribution.source,
            comment=contribution.comment,
            occurred_at=contribution.occurred_at,
            created_at=contribution.created_at,
        )
        self.db.add(record)

        if contribution.type in {ContributionType.ADD, ContributionType.TRANSFER_IN}:
            goal.current_amount += goal_conversion.amount
        elif contribution.type in {ContributionType.SUBTRACT, ContributionType.TRANSFER_OUT}:
            goal.current_amount = max(Decimal("0"), goal.current_amount - goal_conversion.amount)
        elif contribution.type == ContributionType.ADJUSTMENT:
            goal.current_amount = goal_conversion.amount

        refresh_record_status(goal)
        self.audit(
            "goal_contribution",
            record.id,
            "create",
            None,
            contribution_snapshot(record),
        )
        self.audit("financial_goal", goal.id, "contribution_applied", before, goal_snapshot(goal))
        self.db.commit()
        self.db.refresh(record)
        return contribution_to_domain(record)

    def reverse_contribution(self, contribution_id: str) -> GoalContribution | None:
        contribution = self.get_contribution_record(contribution_id)
        if contribution is None:
            return None
        if contribution.reversed_at is not None:
            raise ValueError("Contribution is already reversed")
        if contribution.type == ContributionType.ADJUSTMENT.value:
            raise ValueError("Adjustment contributions cannot be reversed safely")

        goal = self.get_goal_record(contribution.goal_id)
        if goal is None:
            return None

        before_goal = goal_snapshot(goal)
        before_contribution = contribution_snapshot(contribution)

        goal_amount = contribution.amount_in_goal_currency or contribution.amount
        if contribution.type in {ContributionType.ADD.value, ContributionType.TRANSFER_IN.value}:
            goal.current_amount = max(Decimal("0"), goal.current_amount - goal_amount)
        elif contribution.type in {ContributionType.SUBTRACT.value, ContributionType.TRANSFER_OUT.value}:
            goal.current_amount += goal_amount

        contribution.reversed_at = datetime.now(UTC)
        refresh_record_status(goal)

        self.audit(
            "goal_contribution",
            contribution.id,
            "reverse",
            before_contribution,
            contribution_snapshot(contribution),
        )
        self.audit(
            "financial_goal",
            goal.id,
            "contribution_reversed",
            before_goal,
            goal_snapshot(goal),
        )
        self.db.commit()
        self.db.refresh(contribution)
        return contribution_to_domain(contribution)

    def list_contributions(self, goal_id: str) -> list[GoalContribution]:
        if self.get_goal_record(goal_id) is None:
            raise ValueError("Goal not found")

        records = self.db.scalars(
            select(GoalContributionRecord)
            .where(
                GoalContributionRecord.user_id == self.user_id,
                GoalContributionRecord.goal_id == goal_id,
            )
            .order_by(
                GoalContributionRecord.occurred_at.desc(),
                GoalContributionRecord.created_at.desc(),
            )
        ).all()
        return [contribution_to_domain(record) for record in records]

    def get_contribution_record(self, contribution_id: str) -> GoalContributionRecord | None:
        return self.db.scalar(
            select(GoalContributionRecord).where(
                GoalContributionRecord.id == contribution_id,
                GoalContributionRecord.user_id == self.user_id,
            )
        )

    def update_priorities(self, ordered_goal_ids: list[str]) -> list[FinancialGoal]:
        known_ids = set(
            self.db.scalars(
                select(FinancialGoalRecord.id).where(
                    FinancialGoalRecord.user_id == self.user_id,
                    ~FinancialGoalRecord.status.in_(HIDDEN_GOAL_STATUSES),
                )
            )
        )
        unknown_ids = set(ordered_goal_ids) - known_ids
        if unknown_ids:
            raise ValueError(f"Unknown goal ids: {sorted(unknown_ids)}")

        for position, goal_id in enumerate(ordered_goal_ids, start=1):
            record = self.get_goal_record(goal_id)
            if record is None:
                continue
            before = goal_snapshot(record)
            record.priority = position
            self.audit("financial_goal", record.id, "priority_update", before, goal_snapshot(record))

        self.db.commit()
        return self.list_goals()

    def get_plan_settings(self) -> PlanSettings:
        profile = self.get_or_create_profile()
        strategy_record = self.get_or_create_strategy()
        return PlanSettings(
            monthly_available_amount=profile.monthly_available_amount,
            strategy=strategy_to_domain(strategy_record),
        )

    def update_strategy(self, strategy: AllocationStrategy) -> PlanSettings:
        record = self.get_or_create_strategy()
        before = strategy_snapshot(record)
        record.type = strategy.type.value
        record.weights = decimal_dict_to_json(strategy.weights)
        record.fixed_amounts = decimal_dict_to_json(strategy.fixed_amounts)
        self.audit("allocation_strategy", record.id, "update", before, strategy_snapshot(record))
        self.db.commit()
        return self.get_plan_settings()

    def get_goal_record(self, goal_id: str, include_hidden: bool = False) -> FinancialGoalRecord | None:
        query = select(FinancialGoalRecord).where(
            FinancialGoalRecord.id == goal_id,
            FinancialGoalRecord.user_id == self.user_id,
        )
        if not include_hidden:
            query = query.where(~FinancialGoalRecord.status.in_(HIDDEN_GOAL_STATUSES))
        return self.db.scalar(query)

    def get_or_create_profile(self) -> UserProfileRecord:
        profile = self.db.get(UserProfileRecord, self.user_id)
        if profile is not None:
            return profile
        profile = UserProfileRecord(user_id=self.user_id)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_or_create_strategy(self) -> AllocationStrategyRecord:
        record = self.db.scalar(
            select(AllocationStrategyRecord).where(AllocationStrategyRecord.user_id == self.user_id)
        )
        if record is not None:
            return record
        record = AllocationStrategyRecord(user_id=self.user_id)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def audit(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        self.db.add(
            AuditLogRecord(
                actor_user_id=self.user_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                before_json=before,
                after_json=after,
            )
        )


def goal_to_domain(record: FinancialGoalRecord) -> FinancialGoal:
    return FinancialGoal(
        id=record.id,
        title=record.title,
        category=record.category,
        description=record.description,
        target_amount=record.target_amount,
        currency=record.currency,
        current_amount=record.current_amount,
        desired_date=record.desired_date,
        priority=record.priority,
        importance=record.importance,
        deadline_type=DeadlineType(record.deadline_type),
        status=GoalStatus(record.status),
        allocation_weight=record.allocation_weight,
        product_url=record.product_url,
        expected_purchase_date=record.expected_purchase_date,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def contribution_to_domain(record: GoalContributionRecord) -> GoalContribution:
    return GoalContribution(
        id=record.id,
        goal_id=record.goal_id,
        type=ContributionType(record.type),
        amount=record.amount,
        currency=record.currency,
        exchange_rate_id=record.exchange_rate_id,
        exchange_rate=record.exchange_rate,
        amount_in_goal_currency=record.amount_in_goal_currency,
        amount_in_base_currency=record.amount_in_base_currency,
        source=record.source,
        comment=record.comment,
        occurred_at=record.occurred_at,
        created_at=record.created_at,
        reversed_at=record.reversed_at,
    )


def strategy_to_domain(record: AllocationStrategyRecord) -> AllocationStrategy:
    return AllocationStrategy(
        type=AllocationStrategyType(record.type),
        weights=json_to_decimal_dict(record.weights),
        fixed_amounts=json_to_decimal_dict(record.fixed_amounts),
    )


def refresh_record_status(record: FinancialGoalRecord) -> None:
    if record.current_amount >= record.target_amount and record.status == GoalStatus.ACTIVE.value:
        record.status = GoalStatus.REACHED.value
    elif record.current_amount < record.target_amount and record.status == GoalStatus.REACHED.value:
        record.status = GoalStatus.ACTIVE.value


def decimal_dict_to_json(values: dict[str, Decimal]) -> dict[str, str]:
    return {key: str(value) for key, value in values.items()}


def json_to_decimal_dict(values: dict[str, Any] | None) -> dict[str, Decimal]:
    if not values:
        return {}
    return {key: Decimal(str(value)) for key, value in values.items()}


def goal_snapshot(record: FinancialGoalRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "title": record.title,
        "target_amount": str(record.target_amount),
        "currency": record.currency,
        "current_amount": str(record.current_amount),
        "desired_date": serialize_date(record.desired_date),
        "priority": record.priority,
        "deadline_type": record.deadline_type,
        "status": record.status,
        "allocation_weight": str(record.allocation_weight) if record.allocation_weight is not None else None,
    }


def contribution_snapshot(record: GoalContributionRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "goal_id": record.goal_id,
        "type": record.type,
        "amount": str(record.amount),
        "currency": record.currency,
        "exchange_rate_id": record.exchange_rate_id,
        "exchange_rate": str(record.exchange_rate) if record.exchange_rate is not None else None,
        "amount_in_goal_currency": str(record.amount_in_goal_currency) if record.amount_in_goal_currency is not None else None,
        "amount_in_base_currency": str(record.amount_in_base_currency) if record.amount_in_base_currency is not None else None,
        "source": record.source,
        "occurred_at": serialize_date(record.occurred_at),
        "reversed_at": record.reversed_at.isoformat() if record.reversed_at else None,
    }


def price_snapshot(record: GoalPriceHistoryRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "goal_id": record.goal_id,
        "previous_amount": str(record.previous_amount),
        "new_amount": str(record.new_amount),
        "currency": record.currency,
        "source": record.source,
        "changed_at": serialize_date(record.changed_at),
    }


def strategy_snapshot(record: AllocationStrategyRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "type": record.type,
        "weights": record.weights,
        "fixed_amounts": record.fixed_amounts,
    }


def serialize_date(value: date | None) -> str | None:
    return value.isoformat() if value else None
