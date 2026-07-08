from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AllocationStrategyRecord,
    AuditLogRecord,
    DebtRecord,
    EmergencyFundRecord,
    ExpenseRecord,
    FinancialGoalRecord,
    GoalPriceHistoryRecord,
    GoalContributionRecord,
    IncomeRecord,
    NotificationRecord,
    ProductEventRecord,
    RecurringRuleRecord,
    UserProfileRecord,
    UserRecord,
)


class UserExportRepository:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def build_export(self) -> dict[str, Any]:
        user = self.db.get(UserRecord, self.user_id)
        profile = self.db.get(UserProfileRecord, self.user_id)
        payload = {
            "exported_at": datetime.now(UTC).isoformat(),
            "format_version": "2026-07-05",
            "user": record_to_dict(
                user,
                include=["id", "email", "created_at", "updated_at", "deleted_at"],
            )
            if user
            else None,
            "profile": record_to_dict(profile) if profile else None,
            "goals": self.records(FinancialGoalRecord),
            "goal_price_history": self.records(GoalPriceHistoryRecord),
            "goal_contributions": self.records(GoalContributionRecord),
            "incomes": self.records(IncomeRecord),
            "expenses": self.records(ExpenseRecord),
            "debts": self.records(DebtRecord),
            "emergency_fund": self.one_record(EmergencyFundRecord),
            "allocation_strategy": self.one_record(AllocationStrategyRecord),
            "audit_log": self.records(
                AuditLogRecord,
                user_field="actor_user_id",
                order_field=AuditLogRecord.created_at,
            ),
            "notifications": self.records(NotificationRecord),
            "recurring_rules": self.records(RecurringRuleRecord),
            "product_events": self.records(ProductEventRecord),
        }
        self.audit_export()
        return payload

    def records(
        self,
        model: Any,
        user_field: str = "user_id",
        order_field: Any | None = None,
    ) -> list[dict[str, Any]]:
        column = getattr(model, user_field)
        if order_field is None and hasattr(model, "created_at"):
            order_field = getattr(model, "created_at")
        query = select(model).where(column == self.user_id)
        if order_field is not None:
            query = query.order_by(order_field.asc())
        return [record_to_dict(record) for record in self.db.scalars(query)]

    def one_record(self, model: Any, user_field: str = "user_id") -> dict[str, Any] | None:
        column = getattr(model, user_field)
        record = self.db.scalar(select(model).where(column == self.user_id))
        return record_to_dict(record) if record else None

    def audit_export(self) -> None:
        self.db.add(
            AuditLogRecord(
                actor_user_id=self.user_id,
                entity_type="user",
                entity_id=self.user_id,
                action="export",
                before_json=None,
                after_json={"format": "json"},
            )
        )
        self.db.add(
            ProductEventRecord(
                user_id=self.user_id,
                name="data_exported",
                source="api",
                properties={"format": "json"},
            )
        )
        self.db.commit()


def record_to_dict(record: Any, include: list[str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for column in record.__table__.columns:
        if include is not None and column.name not in include:
            continue
        result[column.name] = serialize_value(getattr(record, column.name))
    return result


def serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serialize_value(inner_value) for key, inner_value in value.items()}
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    return value
