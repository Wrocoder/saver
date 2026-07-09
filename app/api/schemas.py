from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.models import (
    AllocationStrategyType,
    ContributionType,
    DeadlineType,
    GoalStatus,
)
from app.domain.finance import DebtStatus, DebtType, MoneyFrequency
from app.domain.planning import FinancialPlanResult


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    target_amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0)
    desired_date: date | None = None
    priority: int = Field(default=1, ge=1)
    importance: int = Field(default=3, ge=1, le=5)
    deadline_type: DeadlineType = DeadlineType.FLEXIBLE
    allocation_weight: Decimal | None = Field(default=None, ge=0, le=100)
    product_url: str | None = Field(default=None, max_length=2048)
    expected_purchase_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    target_amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    current_amount: Decimal | None = Field(default=None, ge=0)
    desired_date: date | None = None
    priority: int | None = Field(default=None, ge=1)
    importance: int | None = Field(default=None, ge=1, le=5)
    deadline_type: DeadlineType | None = None
    allocation_weight: Decimal | None = Field(default=None, ge=0, le=100)
    status: GoalStatus | None = None
    product_url: str | None = Field(default=None, max_length=2048)
    expected_purchase_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str | None
    description: str | None
    target_amount: Decimal
    currency: str
    current_amount: Decimal
    desired_date: date | None
    created_at: datetime
    priority: int
    importance: int
    deadline_type: DeadlineType
    status: GoalStatus
    allocation_weight: Decimal | None
    product_url: str | None
    expected_purchase_date: date | None
    notes: str | None


class GoalPriceHistoryCreate(BaseModel):
    new_amount: Decimal = Field(gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    source: str | None = Field(default="manual", max_length=120)
    note: str | None = Field(default=None, max_length=1000)
    changed_at: date | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class GoalPriceHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    goal_id: str
    previous_amount: Decimal
    new_amount: Decimal
    currency: str
    source: str | None
    note: str | None
    changed_at: date
    created_at: datetime


class ContributionCreate(BaseModel):
    type: ContributionType = ContributionType.ADD
    amount: Decimal = Field(gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    source: str | None = Field(default=None, max_length=120)
    comment: str | None = Field(default=None, max_length=1000)
    occurred_at: date | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class ContributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    goal_id: str
    type: ContributionType
    amount: Decimal
    currency: str
    exchange_rate_id: str | None
    exchange_rate: Decimal | None
    amount_in_goal_currency: Decimal | None
    amount_in_base_currency: Decimal | None
    source: str | None
    comment: str | None
    occurred_at: date
    created_at: datetime
    reversed_at: datetime | None


class PriorityUpdate(BaseModel):
    ordered_goal_ids: list[str] = Field(min_length=1)


class StrategyUpdate(BaseModel):
    type: AllocationStrategyType
    weights: dict[str, Decimal] = Field(default_factory=dict)
    fixed_amounts: dict[str, Decimal] = Field(default_factory=dict)


class StrategyResponse(BaseModel):
    type: AllocationStrategyType
    weights: dict[str, Decimal]
    fixed_amounts: dict[str, Decimal]


class PlanResponse(FinancialPlanResult):
    pass


class ScenarioRequest(BaseModel):
    scenario_name: str = Field(default="monthly_amount_change", max_length=120)
    monthly_available_amount: Decimal = Field(gt=0)


class OneTimeInflowScenarioRequest(BaseModel):
    scenario_name: str = Field(default="one_time_inflow", max_length=120)
    amount: Decimal = Field(gt=0)
    month_index: int = Field(ge=1, le=600)


class ScenarioResponse(BaseModel):
    scenario_name: str
    base: FinancialPlanResult
    scenario: FinancialPlanResult


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str | None = Field(default=None, max_length=120)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("base_currency")
    @classmethod
    def normalize_base_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None
    base_currency: str


class AuthRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=120)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("base_currency")
    @classmethod
    def normalize_base_currency(cls, value: str) -> str:
        return value.upper()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class AuthRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class AuthTokenResponse(BaseModel):
    token_type: str = "bearer"
    access_token: str
    refresh_token: str


class AuthResponse(AuthTokenResponse):
    user: UserResponse


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None
    country: str | None
    timezone: str
    language: str
    base_currency: str
    income_type: str | None
    average_monthly_income: Decimal | None
    mandatory_monthly_expenses: Decimal | None
    monthly_available_amount: Decimal
    desired_min_balance: Decimal | None


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, max_length=10)
    base_currency: str | None = Field(default=None, min_length=3, max_length=3)
    income_type: str | None = Field(default=None, max_length=30)
    average_monthly_income: Decimal | None = Field(default=None, ge=0)
    mandatory_monthly_expenses: Decimal | None = Field(default=None, ge=0)
    monthly_available_amount: Decimal | None = Field(default=None, ge=0)
    desired_min_balance: Decimal | None = Field(default=None, ge=0)

    @field_validator("base_currency")
    @classmethod
    def normalize_base_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class IncomeCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    frequency: MoneyFrequency = MoneyFrequency.MONTHLY
    source: str | None = Field(default=None, max_length=120)
    is_recurring: bool = True
    received_at: date | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class IncomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    amount: Decimal
    currency: str
    frequency: MoneyFrequency
    source: str | None
    is_recurring: bool
    received_at: date | None
    created_at: datetime


class IncomeUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    frequency: MoneyFrequency | None = None
    source: str | None = Field(default=None, max_length=120)
    is_recurring: bool | None = None
    received_at: date | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class ExpenseCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    category: str = Field(min_length=1, max_length=120)
    frequency: MoneyFrequency = MoneyFrequency.MONTHLY
    is_mandatory: bool = True
    is_recurring: bool = True
    occurred_at: date | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    amount: Decimal
    currency: str
    category: str
    frequency: MoneyFrequency
    is_mandatory: bool
    is_recurring: bool
    occurred_at: date | None
    created_at: datetime


class ExpenseUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    frequency: MoneyFrequency | None = None
    is_mandatory: bool | None = None
    is_recurring: bool | None = None
    occurred_at: date | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class DebtCreate(BaseModel):
    type: DebtType = DebtType.OTHER
    creditor: str | None = Field(default=None, max_length=120)
    balance: Decimal = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    interest_rate: Decimal | None = Field(default=None, ge=0)
    min_monthly_payment: Decimal = Field(default=Decimal("0"), ge=0)
    due_day: int | None = Field(default=None, ge=1, le=31)
    status: DebtStatus = DebtStatus.ACTIVE

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class DebtResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: DebtType
    creditor: str | None
    balance: Decimal
    currency: str
    interest_rate: Decimal | None
    min_monthly_payment: Decimal
    due_day: int | None
    status: DebtStatus
    created_at: datetime


class DebtUpdate(BaseModel):
    type: DebtType | None = None
    creditor: str | None = Field(default=None, max_length=120)
    balance: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    interest_rate: Decimal | None = Field(default=None, ge=0)
    min_monthly_payment: Decimal | None = Field(default=None, ge=0)
    due_day: int | None = Field(default=None, ge=1, le=31)
    status: DebtStatus | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class EmergencyFundUpsert(BaseModel):
    target_months: int = Field(default=3, ge=1, le=24)
    target_amount: Decimal = Field(default=Decimal("0"), ge=0)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0)
    monthly_contribution: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class EmergencyFundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target_months: int
    target_amount: Decimal
    current_amount: Decimal
    monthly_contribution: Decimal
    currency: str
    created_at: datetime


class FinancialSummaryResponse(BaseModel):
    base_currency: str
    manual_monthly_available_amount: Decimal
    total_monthly_income: Decimal
    total_monthly_expenses: Decimal
    total_monthly_debt_payments: Decimal
    emergency_fund_gap: Decimal
    emergency_fund_monthly_reserve: Decimal
    calculated_monthly_available_amount: Decimal
    effective_monthly_available_amount: Decimal
    has_financial_inputs: bool
    assumptions: list[str]
    warnings: list[str]


class CurrencyCreate(BaseModel):
    code: str = Field(min_length=3, max_length=3)
    symbol: str | None = Field(default=None, max_length=8)
    name: str = Field(min_length=1, max_length=80)
    decimals: int = Field(default=2, ge=0, le=8)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()


class CurrencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    symbol: str | None
    name: str
    decimals: int


class ExchangeRateCreate(BaseModel):
    base_currency: str = Field(min_length=3, max_length=3)
    quote_currency: str = Field(min_length=3, max_length=3)
    rate: Decimal = Field(gt=0)
    source: str | None = Field(default=None, max_length=120)
    rate_date: date

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class ExchangeRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    base_currency: str
    quote_currency: str
    rate: Decimal
    source: str | None
    rate_date: date
    created_at: datetime


class AnalyticsEventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source: str = Field(default="web", min_length=1, max_length=40)
    properties: dict[str, Any] = Field(default_factory=dict)


class AnalyticsEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    source: str
    properties: dict[str, Any]
    created_at: datetime


class AnalyticsEventCount(BaseModel):
    name: str
    count: int


class AnalyticsSummaryResponse(BaseModel):
    total_events: int
    events_last_7_days: int
    events_last_30_days: int
    active_days_last_30: int
    last_event_at: datetime | None
    key_metrics: dict[str, int]
    event_counts: list[AnalyticsEventCount]
    recent_events: list[AnalyticsEventResponse]


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: str | None
    entity_type: str
    entity_id: str
    action: str
    before_json: dict[str, Any] | None
    after_json: dict[str, Any] | None
    created_at: datetime


class CsvImportRequest(BaseModel):
    csv_text: str = Field(min_length=1)


class CsvImportErrorDetail(BaseModel):
    row_number: int | None
    field: str | None
    value: str | None
    message: str


class CsvGoalImportResponse(BaseModel):
    created_count: int
    skipped_count: int
    errors: list[str]
    error_details: list[CsvImportErrorDetail]
    created_goals: list[GoalResponse]


class CsvContributionImportResponse(BaseModel):
    created_count: int
    skipped_count: int
    errors: list[str]
    error_details: list[CsvImportErrorDetail]
    created_contributions: list[ContributionResponse]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    type: str
    title: str
    body: str
    channel: str
    severity: str
    status: str
    metadata_json: dict[str, Any]
    scheduled_for: datetime | None
    read_at: datetime | None
    created_at: datetime


NotificationFrequency = Literal["instant", "daily", "weekly", "monthly"]


class NotificationSettingsResponse(BaseModel):
    in_app_enabled: bool
    plan_warnings: bool
    milestone_updates: bool
    monthly_reminders: bool
    email_enabled: bool
    in_app_frequency: NotificationFrequency
    email_frequency: NotificationFrequency


class NotificationSettingsUpdate(BaseModel):
    in_app_enabled: bool | None = None
    plan_warnings: bool | None = None
    milestone_updates: bool | None = None
    monthly_reminders: bool | None = None
    email_enabled: bool | None = None
    in_app_frequency: NotificationFrequency | None = None
    email_frequency: NotificationFrequency | None = None


class RecurringRuleCreate(BaseModel):
    goal_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=160)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    frequency: MoneyFrequency = MoneyFrequency.MONTHLY
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    source: str | None = Field(default=None, max_length=120)
    next_run_on: date | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class RecurringRuleUpdate(BaseModel):
    goal_id: str | None = Field(default=None, min_length=1)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    frequency: MoneyFrequency | None = None
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    source: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
    next_run_on: date | None = None

    @field_validator("currency")
    @classmethod
    def normalize_optional_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class RecurringRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    goal_id: str
    title: str
    amount: Decimal
    currency: str
    frequency: MoneyFrequency
    day_of_month: int | None
    source: str | None
    is_active: bool
    next_run_on: date | None
    last_run_on: date | None
    created_at: datetime
    updated_at: datetime


class MonthlyGoalReport(BaseModel):
    goal_id: str
    title: str
    currency: str
    added_amount: Decimal
    removed_amount: Decimal
    net_amount: Decimal
    contributions_count: int
    current_amount: Decimal
    target_amount: Decimal
    progress_percent: Decimal
    status: str


class MonthlyReportResponse(BaseModel):
    period_start: date
    period_end: date
    base_currency: str
    total_added: Decimal
    total_removed: Decimal
    net_saved: Decimal
    contributions_count: int
    reversed_contributions_count: int
    safe_monthly_capacity: Decimal
    goal_reports: list[MonthlyGoalReport]
    plan_recommendations: list[str]
    plan_conflicts: list[str]
    warnings: list[str]
