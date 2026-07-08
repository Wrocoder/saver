from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLogRecord, RecurringRuleRecord
from app.domain.finance import MoneyFrequency
from app.domain.models import ContributionType, GoalContribution
from app.domain.planning import add_months
from app.repositories.sqlalchemy import GoalsRepository


class RecurringRulesRepository:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def list_rules(self, active_only: bool = False) -> list[RecurringRuleRecord]:
        query = select(RecurringRuleRecord).where(RecurringRuleRecord.user_id == self.user_id)
        if active_only:
            query = query.where(RecurringRuleRecord.is_active.is_(True))
        query = query.order_by(RecurringRuleRecord.next_run_on.asc(), RecurringRuleRecord.created_at.desc())
        return list(self.db.scalars(query))

    def create_rule(
        self,
        goal_id: str,
        title: str,
        amount: Decimal,
        currency: str,
        frequency: str,
        day_of_month: int | None,
        source: str | None,
        next_run_on: date | None,
    ) -> RecurringRuleRecord:
        self.ensure_goal_exists(goal_id)
        record = RecurringRuleRecord(
            user_id=self.user_id,
            goal_id=goal_id,
            title=title,
            amount=amount,
            currency=currency,
            frequency=frequency,
            day_of_month=day_of_month,
            source=source,
            next_run_on=next_run_on or date.today(),
        )
        self.db.add(record)
        self.db.flush()
        self.audit("recurring_rule", record.id, "create", None, rule_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_rule(self, rule_id: str, updates: dict[str, Any]) -> RecurringRuleRecord | None:
        record = self.get_rule_record(rule_id)
        if record is None:
            return None
        if "goal_id" in updates:
            self.ensure_goal_exists(updates["goal_id"])

        before = rule_snapshot(record)
        for key, value in updates.items():
            if hasattr(value, "value"):
                value = value.value
            setattr(record, key, value)

        self.audit("recurring_rule", record.id, "update", before, rule_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_rule(self, rule_id: str) -> bool:
        record = self.get_rule_record(rule_id)
        if record is None:
            return False

        before = rule_snapshot(record)
        self.audit("recurring_rule", record.id, "delete", before, None)
        self.db.delete(record)
        self.db.commit()
        return True

    def apply_rule(self, rule_id: str, occurred_at: date | None = None) -> GoalContribution:
        record = self.get_rule_record(rule_id)
        if record is None:
            raise ValueError("Recurring rule not found")
        if not record.is_active:
            raise ValueError("Recurring rule is paused")

        occurred_at = occurred_at or date.today()
        before = rule_snapshot(record)
        contribution = GoalContribution(
            goal_id=record.goal_id,
            type=ContributionType.ADD,
            amount=record.amount,
            currency=record.currency,
            source=record.source or record.title,
            comment=f"Applied recurring rule: {record.title}",
            occurred_at=occurred_at,
        )
        applied = GoalsRepository(self.db, self.user_id).add_contribution(contribution)

        record.last_run_on = occurred_at
        record.next_run_on = next_run_date(
            frequency=MoneyFrequency(record.frequency),
            current=occurred_at,
            day_of_month=record.day_of_month,
        )
        self.audit("recurring_rule", record.id, "apply", before, rule_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return applied

    def get_rule_record(self, rule_id: str) -> RecurringRuleRecord | None:
        return self.db.scalar(
            select(RecurringRuleRecord).where(
                RecurringRuleRecord.id == rule_id,
                RecurringRuleRecord.user_id == self.user_id,
            )
        )

    def ensure_goal_exists(self, goal_id: str) -> None:
        if GoalsRepository(self.db, self.user_id).get_goal(goal_id) is None:
            raise ValueError("Goal not found")

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


def next_run_date(frequency: MoneyFrequency, current: date, day_of_month: int | None = None) -> date:
    if frequency == MoneyFrequency.WEEKLY:
        return date.fromordinal(current.toordinal() + 7)
    if frequency == MoneyFrequency.BIWEEKLY:
        return date.fromordinal(current.toordinal() + 14)
    if frequency == MoneyFrequency.ANNUAL:
        next_year = date(current.year + 1, current.month, 1)
        return with_day(next_year, day_of_month or current.day)
    if frequency == MoneyFrequency.ONE_TIME:
        return current
    next_month = add_months(current.replace(day=1), 1)
    return with_day(next_month, day_of_month or current.day)


def with_day(value: date, day: int) -> date:
    next_month = add_months(value.replace(day=1), 1)
    last_day = date.fromordinal(next_month.toordinal() - 1).day
    return value.replace(day=min(max(day, 1), last_day))


def rule_snapshot(record: RecurringRuleRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "goal_id": record.goal_id,
        "title": record.title,
        "amount": str(record.amount),
        "currency": record.currency,
        "frequency": record.frequency,
        "day_of_month": record.day_of_month,
        "source": record.source,
        "is_active": record.is_active,
        "next_run_on": record.next_run_on.isoformat() if record.next_run_on else None,
        "last_run_on": record.last_run_on.isoformat() if record.last_run_on else None,
    }
