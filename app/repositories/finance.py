from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AuditLogRecord,
    DebtRecord,
    EmergencyFundRecord,
    ExpenseRecord,
    IncomeRecord,
    UserProfileRecord,
)
from app.domain.finance import DebtStatus, MoneyFrequency, monthly_equivalent
from app.repositories.currency import CurrencyRepository, MissingExchangeRateError


@dataclass(frozen=True, slots=True)
class FinancialSummary:
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


class FinanceRepository:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id
        self.currency_repo = CurrencyRepository(db)

    def get_profile(self) -> UserProfileRecord:
        profile = self.db.get(UserProfileRecord, self.user_id)
        if profile is not None:
            return profile

        profile = UserProfileRecord(user_id=self.user_id)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_profile(self, updates: dict[str, Any]) -> UserProfileRecord:
        profile = self.get_profile()
        before = profile_snapshot(profile)

        for key, value in updates.items():
            setattr(profile, key, value)

        self.audit("user_profile", profile.user_id, "update", before, profile_snapshot(profile))
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def list_incomes(self) -> list[IncomeRecord]:
        return list(
            self.db.scalars(
                select(IncomeRecord)
                .where(IncomeRecord.user_id == self.user_id)
                .order_by(IncomeRecord.created_at.desc())
            )
        )

    def add_income(
        self,
        amount: Decimal,
        currency: str,
        frequency: str,
        source: str | None,
        is_recurring: bool,
        received_at,
    ) -> IncomeRecord:
        record = IncomeRecord(
            user_id=self.user_id,
            amount=amount,
            currency=currency,
            frequency=frequency,
            source=source,
            is_recurring=is_recurring,
            received_at=received_at,
        )
        self.db.add(record)
        self.db.flush()
        self.audit("income", record.id, "create", None, income_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_income(self, income_id: str, updates: dict[str, Any]) -> IncomeRecord | None:
        record = self.get_income_record(income_id)
        if record is None:
            return None

        before = income_snapshot(record)
        apply_updates(record, updates)
        self.audit("income", record.id, "update", before, income_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_income(self, income_id: str) -> bool:
        record = self.get_income_record(income_id)
        if record is None:
            return False

        before = income_snapshot(record)
        self.audit("income", record.id, "delete", before, None)
        self.db.delete(record)
        self.db.commit()
        return True

    def get_income_record(self, income_id: str) -> IncomeRecord | None:
        return self.db.scalar(
            select(IncomeRecord).where(
                IncomeRecord.id == income_id,
                IncomeRecord.user_id == self.user_id,
            )
        )

    def list_expenses(self) -> list[ExpenseRecord]:
        return list(
            self.db.scalars(
                select(ExpenseRecord)
                .where(ExpenseRecord.user_id == self.user_id)
                .order_by(ExpenseRecord.created_at.desc())
            )
        )

    def add_expense(
        self,
        amount: Decimal,
        currency: str,
        category: str,
        frequency: str,
        is_mandatory: bool,
        is_recurring: bool,
        occurred_at,
    ) -> ExpenseRecord:
        record = ExpenseRecord(
            user_id=self.user_id,
            amount=amount,
            currency=currency,
            category=category,
            frequency=frequency,
            is_mandatory=is_mandatory,
            is_recurring=is_recurring,
            occurred_at=occurred_at,
        )
        self.db.add(record)
        self.db.flush()
        self.audit("expense", record.id, "create", None, expense_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_expense(self, expense_id: str, updates: dict[str, Any]) -> ExpenseRecord | None:
        record = self.get_expense_record(expense_id)
        if record is None:
            return None

        before = expense_snapshot(record)
        apply_updates(record, updates)
        self.audit("expense", record.id, "update", before, expense_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_expense(self, expense_id: str) -> bool:
        record = self.get_expense_record(expense_id)
        if record is None:
            return False

        before = expense_snapshot(record)
        self.audit("expense", record.id, "delete", before, None)
        self.db.delete(record)
        self.db.commit()
        return True

    def get_expense_record(self, expense_id: str) -> ExpenseRecord | None:
        return self.db.scalar(
            select(ExpenseRecord).where(
                ExpenseRecord.id == expense_id,
                ExpenseRecord.user_id == self.user_id,
            )
        )

    def list_debts(self) -> list[DebtRecord]:
        return list(
            self.db.scalars(
                select(DebtRecord)
                .where(DebtRecord.user_id == self.user_id)
                .order_by(DebtRecord.created_at.desc())
            )
        )

    def add_debt(
        self,
        debt_type: str,
        creditor: str | None,
        balance: Decimal,
        currency: str,
        interest_rate: Decimal | None,
        min_monthly_payment: Decimal,
        due_day: int | None,
        status: str,
    ) -> DebtRecord:
        record = DebtRecord(
            user_id=self.user_id,
            type=debt_type,
            creditor=creditor,
            balance=balance,
            currency=currency,
            interest_rate=interest_rate,
            min_monthly_payment=min_monthly_payment,
            due_day=due_day,
            status=status,
        )
        self.db.add(record)
        self.db.flush()
        self.audit("debt", record.id, "create", None, debt_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_debt(self, debt_id: str, updates: dict[str, Any]) -> DebtRecord | None:
        record = self.get_debt_record(debt_id)
        if record is None:
            return None

        before = debt_snapshot(record)
        apply_updates(record, updates)
        self.audit("debt", record.id, "update", before, debt_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_debt(self, debt_id: str) -> bool:
        record = self.get_debt_record(debt_id)
        if record is None:
            return False

        before = debt_snapshot(record)
        self.audit("debt", record.id, "delete", before, None)
        self.db.delete(record)
        self.db.commit()
        return True

    def get_debt_record(self, debt_id: str) -> DebtRecord | None:
        return self.db.scalar(
            select(DebtRecord).where(
                DebtRecord.id == debt_id,
                DebtRecord.user_id == self.user_id,
            )
        )

    def get_emergency_fund(self) -> EmergencyFundRecord | None:
        return self.db.scalar(
            select(EmergencyFundRecord).where(EmergencyFundRecord.user_id == self.user_id)
        )

    def upsert_emergency_fund(
        self,
        target_months: int,
        target_amount: Decimal,
        current_amount: Decimal,
        monthly_contribution: Decimal,
        currency: str,
    ) -> EmergencyFundRecord:
        record = self.get_emergency_fund()
        if record is None:
            record = EmergencyFundRecord(user_id=self.user_id)
            self.db.add(record)
            before = None
            action = "create"
        else:
            before = emergency_fund_snapshot(record)
            action = "update"

        record.target_months = target_months
        record.target_amount = target_amount
        record.current_amount = current_amount
        record.monthly_contribution = monthly_contribution
        record.currency = currency
        self.db.flush()
        self.audit("emergency_fund", record.id, action, before, emergency_fund_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def build_summary(self) -> FinancialSummary:
        profile = self.get_profile()
        incomes = self.list_incomes()
        expenses = self.list_expenses()
        debts = self.list_debts()
        emergency_fund = self.get_emergency_fund()
        base_currency = profile.base_currency
        assumptions = [
            "Only recurring entries are converted into monthly equivalents.",
            "One-time income and expenses are kept for history but are not included in the monthly plan yet.",
        ]
        warnings: list[str] = []

        total_income = Decimal("0")
        total_expenses = Decimal("0")
        total_debt_payments = Decimal("0")
        missing_exchange_rates: set[str] = set()

        for income in incomes:
            monthly_amount = monthly_equivalent(
                income.amount,
                MoneyFrequency(income.frequency),
                income.is_recurring,
            )
            converted_amount = self.convert_to_base_or_none(
                monthly_amount,
                income.currency,
                base_currency,
                missing_exchange_rates,
            )
            if converted_amount is None:
                continue
            total_income += converted_amount

        for expense in expenses:
            monthly_amount = monthly_equivalent(
                expense.amount,
                MoneyFrequency(expense.frequency),
                expense.is_recurring,
            )
            converted_amount = self.convert_to_base_or_none(
                monthly_amount,
                expense.currency,
                base_currency,
                missing_exchange_rates,
            )
            if converted_amount is None:
                continue
            total_expenses += converted_amount

        for debt in debts:
            if debt.status != DebtStatus.ACTIVE.value:
                continue
            converted_amount = self.convert_to_base_or_none(
                debt.min_monthly_payment,
                debt.currency,
                base_currency,
                missing_exchange_rates,
            )
            if converted_amount is None:
                continue
            total_debt_payments += converted_amount

        if not incomes and profile.average_monthly_income is not None:
            total_income = profile.average_monthly_income
            assumptions.append("Profile average monthly income is used because no income records exist.")

        if not expenses and profile.mandatory_monthly_expenses is not None:
            total_expenses = profile.mandatory_monthly_expenses
            assumptions.append("Profile mandatory monthly expenses are used because no expense records exist.")

        emergency_gap = Decimal("0")
        emergency_reserve = Decimal("0")
        if emergency_fund is not None:
            target_amount = self.convert_to_base_or_none(
                emergency_fund.target_amount,
                emergency_fund.currency,
                base_currency,
                missing_exchange_rates,
            )
            current_amount = self.convert_to_base_or_none(
                emergency_fund.current_amount,
                emergency_fund.currency,
                base_currency,
                missing_exchange_rates,
            )
            monthly_contribution = self.convert_to_base_or_none(
                emergency_fund.monthly_contribution,
                emergency_fund.currency,
                base_currency,
                missing_exchange_rates,
            )
            if (
                target_amount is not None
                and current_amount is not None
                and monthly_contribution is not None
            ):
                emergency_gap = max(Decimal("0"), target_amount - current_amount)
                if emergency_gap > 0:
                    emergency_reserve = min(monthly_contribution, emergency_gap)

        if missing_exchange_rates:
            warnings.append(
                "Missing exchange rates for: "
                + ", ".join(sorted(missing_exchange_rates))
                + ". Those inputs are excluded from the monthly plan."
            )

        if not missing_exchange_rates and any(
            record.currency != base_currency
            for record in [*incomes, *expenses, *debts]
        ):
            assumptions.append(
                "Non-base-currency inputs are converted using the latest stored exchange rates."
            )
        if emergency_fund is not None and emergency_fund.currency != base_currency:
            assumptions.append(
                "Emergency fund values are converted using the latest stored exchange rates."
            )

        calculated = max(
            Decimal("0"),
            total_income - total_expenses - total_debt_payments - emergency_reserve,
        )
        manual = profile.monthly_available_amount
        has_inputs = bool(
            incomes
            or expenses
            or debts
            or emergency_fund
            or profile.average_monthly_income is not None
            or profile.mandatory_monthly_expenses is not None
        )
        effective = min(manual, calculated) if has_inputs else manual

        if has_inputs and calculated < manual:
            warnings.append(
                "Manual savings amount is higher than calculated safe capacity; the plan uses the lower value."
            )

        return FinancialSummary(
            base_currency=base_currency,
            manual_monthly_available_amount=manual,
            total_monthly_income=total_income,
            total_monthly_expenses=total_expenses,
            total_monthly_debt_payments=total_debt_payments,
            emergency_fund_gap=emergency_gap,
            emergency_fund_monthly_reserve=emergency_reserve,
            calculated_monthly_available_amount=calculated,
            effective_monthly_available_amount=effective,
            has_financial_inputs=has_inputs,
            assumptions=assumptions,
            warnings=warnings,
        )

    def convert_to_base_or_none(
        self,
        amount: Decimal,
        source_currency: str,
        base_currency: str,
        missing_exchange_rates: set[str],
    ) -> Decimal | None:
        try:
            return self.currency_repo.convert(amount, source_currency, base_currency).amount
        except MissingExchangeRateError:
            missing_exchange_rates.add(f"{source_currency}->{base_currency}")
            return None

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


def profile_snapshot(record: UserProfileRecord) -> dict[str, Any]:
    return {
        "user_id": record.user_id,
        "name": record.name,
        "country": record.country,
        "timezone": record.timezone,
        "language": record.language,
        "base_currency": record.base_currency,
        "income_type": record.income_type,
        "average_monthly_income": str(record.average_monthly_income) if record.average_monthly_income is not None else None,
        "mandatory_monthly_expenses": str(record.mandatory_monthly_expenses) if record.mandatory_monthly_expenses is not None else None,
        "monthly_available_amount": str(record.monthly_available_amount),
        "desired_min_balance": str(record.desired_min_balance) if record.desired_min_balance is not None else None,
    }


def income_snapshot(record: IncomeRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "amount": str(record.amount),
        "currency": record.currency,
        "frequency": record.frequency,
        "source": record.source,
        "is_recurring": record.is_recurring,
    }


def expense_snapshot(record: ExpenseRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "amount": str(record.amount),
        "currency": record.currency,
        "category": record.category,
        "frequency": record.frequency,
        "is_mandatory": record.is_mandatory,
        "is_recurring": record.is_recurring,
    }


def debt_snapshot(record: DebtRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "type": record.type,
        "creditor": record.creditor,
        "balance": str(record.balance),
        "currency": record.currency,
        "interest_rate": str(record.interest_rate) if record.interest_rate is not None else None,
        "min_monthly_payment": str(record.min_monthly_payment),
        "status": record.status,
    }


def emergency_fund_snapshot(record: EmergencyFundRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "target_months": record.target_months,
        "target_amount": str(record.target_amount),
        "current_amount": str(record.current_amount),
        "monthly_contribution": str(record.monthly_contribution),
        "currency": record.currency,
    }


def apply_updates(record: Any, updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if hasattr(value, "value"):
            value = value.value
        setattr(record, key, value)
