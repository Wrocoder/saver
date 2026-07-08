from decimal import Decimal
from enum import StrEnum


class MoneyFrequency(StrEnum):
    ONE_TIME = "one_time"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    ANNUAL = "annual"


class DebtType(StrEnum):
    LOAN = "loan"
    CREDIT_CARD = "credit_card"
    INSTALLMENT = "installment"
    PERSONAL_DEBT = "personal_debt"
    OTHER = "other"


class DebtStatus(StrEnum):
    ACTIVE = "active"
    PAID = "paid"
    PAUSED = "paused"


WEEKS_IN_MONTH = Decimal("4.345")
BIWEEKS_IN_MONTH = Decimal("2.1725")
MONTHS_IN_YEAR = Decimal("12")


def monthly_equivalent(
    amount: Decimal,
    frequency: MoneyFrequency,
    is_recurring: bool = True,
) -> Decimal:
    if not is_recurring or frequency == MoneyFrequency.ONE_TIME:
        return Decimal("0")
    if frequency == MoneyFrequency.WEEKLY:
        return amount * WEEKS_IN_MONTH
    if frequency == MoneyFrequency.BIWEEKLY:
        return amount * BIWEEKS_IN_MONTH
    if frequency == MoneyFrequency.ANNUAL:
        return amount / MONTHS_IN_YEAR
    return amount
