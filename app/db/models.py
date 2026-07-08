from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_uuid() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped["UserProfileRecord"] = relationship(back_populates="user", uselist=False)
    goals: Mapped[list["FinancialGoalRecord"]] = relationship(back_populates="user")


class UserProfileRecord(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    timezone: Mapped[str] = mapped_column(String(80), default="Europe/Warsaw")
    language: Mapped[str] = mapped_column(String(10), default="ru")
    base_currency: Mapped[str] = mapped_column(String(3), default="USD")
    income_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    average_monthly_income: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    mandatory_monthly_expenses: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    monthly_available_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("300"))
    desired_min_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    notification_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped[UserRecord] = relationship(back_populates="profile")


class CurrencyRecord(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(8), nullable=True)
    name: Mapped[str] = mapped_column(String(80))
    decimals: Mapped[int] = mapped_column(Integer, default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ExchangeRateRecord(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    base_currency: Mapped[str] = mapped_column(String(3), index=True)
    quote_currency: Mapped[str] = mapped_column(String(3), index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 10))
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rate_date: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FinancialGoalRecord(Base):
    __tablename__ = "financial_goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    desired_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    importance: Mapped[int] = mapped_column(Integer, default=3)
    deadline_type: Mapped[str] = mapped_column(String(30), default="flexible")
    status: Mapped[str] = mapped_column(String(30), default="active")
    allocation_weight: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    product_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    expected_purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped[UserRecord] = relationship(back_populates="goals")
    contributions: Mapped[list["GoalContributionRecord"]] = relationship(back_populates="goal")


class GoalContributionRecord(Base):
    __tablename__ = "goal_contributions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    goal_id: Mapped[str] = mapped_column(ForeignKey("financial_goals.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(30))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3))
    exchange_rate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    amount_in_goal_currency: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    amount_in_base_currency: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    goal: Mapped[FinancialGoalRecord] = relationship(back_populates="contributions")


class IncomeRecord(Base):
    __tablename__ = "incomes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3))
    frequency: Mapped[str] = mapped_column(String(30), default="monthly")
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_recurring: Mapped[bool] = mapped_column(default=True)
    received_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ExpenseRecord(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3))
    category: Mapped[str] = mapped_column(String(120))
    frequency: Mapped[str] = mapped_column(String(30), default="monthly")
    is_mandatory: Mapped[bool] = mapped_column(default=True)
    is_recurring: Mapped[bool] = mapped_column(default=True)
    occurred_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class DebtRecord(Base):
    __tablename__ = "debts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    creditor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3))
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    min_monthly_payment: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    due_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class EmergencyFundRecord(Base):
    __tablename__ = "emergency_funds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    target_months: Mapped[int] = mapped_column(Integer, default=3)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    monthly_contribution: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AllocationStrategyRecord(Base):
    __tablename__ = "allocation_strategies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(40), default="strict_priority")
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
    fixed_amounts: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AuthRefreshTokenRecord(Base):
    __tablename__ = "auth_refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_token_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditLogRecord(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    action: Mapped[str] = mapped_column(String(80))
    before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProductEventRecord(Base):
    __tablename__ = "product_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    source: Mapped[str] = mapped_column(String(40), default="web")
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class NotificationRecord(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(40), default="in_app")
    severity: Mapped[str] = mapped_column(String(30), default="info")
    status: Mapped[str] = mapped_column(String(30), default="unread", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RecurringRuleRecord(Base):
    __tablename__ = "recurring_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("financial_goals.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3))
    frequency: Mapped[str] = mapped_column(String(30), default="monthly")
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    next_run_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_run_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class GoalPriceHistoryRecord(Base):
    __tablename__ = "goal_price_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("financial_goals.id"), index=True)
    previous_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    new_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3))
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
