from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CurrencyRecord, ExchangeRateRecord


class MissingExchangeRateError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ConversionResult:
    amount: Decimal
    rate: Decimal
    exchange_rate_id: str | None
    source_currency: str
    target_currency: str
    rate_date: object | None
    rate_source: str | None


class CurrencyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_currencies(self) -> list[CurrencyRecord]:
        return list(
            self.db.scalars(select(CurrencyRecord).order_by(CurrencyRecord.code.asc()))
        )

    def upsert_currency(
        self,
        code: str,
        name: str,
        symbol: str | None,
        decimals: int,
    ) -> CurrencyRecord:
        record = self.db.get(CurrencyRecord, code)
        if record is None:
            record = CurrencyRecord(code=code, name=name, symbol=symbol, decimals=decimals)
            self.db.add(record)
        else:
            record.name = name
            record.symbol = symbol
            record.decimals = decimals
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_exchange_rates(self) -> list[ExchangeRateRecord]:
        return list(
            self.db.scalars(
                select(ExchangeRateRecord).order_by(
                    ExchangeRateRecord.rate_date.desc(),
                    ExchangeRateRecord.created_at.desc(),
                )
            )
        )

    def add_exchange_rate(
        self,
        base_currency: str,
        quote_currency: str,
        rate: Decimal,
        source: str | None,
        rate_date,
    ) -> ExchangeRateRecord:
        record = ExchangeRateRecord(
            base_currency=base_currency,
            quote_currency=quote_currency,
            rate=rate,
            source=source,
            rate_date=rate_date,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def convert(
        self,
        amount: Decimal,
        source_currency: str,
        target_currency: str,
    ) -> ConversionResult:
        source_currency = source_currency.upper()
        target_currency = target_currency.upper()
        if source_currency == target_currency:
            return ConversionResult(
                amount=amount,
                rate=Decimal("1"),
                exchange_rate_id=None,
                source_currency=source_currency,
                target_currency=target_currency,
                rate_date=None,
                rate_source=None,
            )

        direct_rate = self.latest_rate(source_currency, target_currency)
        if direct_rate is not None:
            return ConversionResult(
                amount=amount * direct_rate.rate,
                rate=direct_rate.rate,
                exchange_rate_id=direct_rate.id,
                source_currency=source_currency,
                target_currency=target_currency,
                rate_date=direct_rate.rate_date,
                rate_source=direct_rate.source,
            )

        inverse_rate = self.latest_rate(target_currency, source_currency)
        if inverse_rate is not None:
            inverse = Decimal("1") / inverse_rate.rate
            return ConversionResult(
                amount=amount * inverse,
                rate=inverse,
                exchange_rate_id=inverse_rate.id,
                source_currency=source_currency,
                target_currency=target_currency,
                rate_date=inverse_rate.rate_date,
                rate_source=inverse_rate.source,
            )

        raise MissingExchangeRateError(
            f"Missing exchange rate for {source_currency}->{target_currency}"
        )

    def latest_rate(
        self,
        base_currency: str,
        quote_currency: str,
    ) -> ExchangeRateRecord | None:
        return self.db.scalar(
            select(ExchangeRateRecord)
            .where(
                ExchangeRateRecord.base_currency == base_currency.upper(),
                ExchangeRateRecord.quote_currency == quote_currency.upper(),
            )
            .order_by(
                ExchangeRateRecord.rate_date.desc(),
                ExchangeRateRecord.created_at.desc(),
            )
        )
