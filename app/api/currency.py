from fastapi import APIRouter, Depends, status

from app.api.deps import get_currency_repository
from app.api.schemas import (
    CurrencyCreate,
    CurrencyResponse,
    ExchangeRateCreate,
    ExchangeRateResponse,
)
from app.db.models import CurrencyRecord, ExchangeRateRecord
from app.repositories.currency import CurrencyRepository


router = APIRouter(prefix="/api", tags=["currency"])


@router.get("/currencies", response_model=list[CurrencyResponse])
def list_currencies(
    repo: CurrencyRepository = Depends(get_currency_repository),
) -> list[CurrencyRecord]:
    return repo.list_currencies()


@router.post("/currencies", response_model=CurrencyResponse, status_code=status.HTTP_201_CREATED)
def upsert_currency(
    payload: CurrencyCreate,
    repo: CurrencyRepository = Depends(get_currency_repository),
) -> CurrencyRecord:
    return repo.upsert_currency(
        code=payload.code,
        name=payload.name,
        symbol=payload.symbol,
        decimals=payload.decimals,
    )


@router.get("/exchange-rates", response_model=list[ExchangeRateResponse])
def list_exchange_rates(
    repo: CurrencyRepository = Depends(get_currency_repository),
) -> list[ExchangeRateRecord]:
    return repo.list_exchange_rates()


@router.post(
    "/exchange-rates",
    response_model=ExchangeRateResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_exchange_rate(
    payload: ExchangeRateCreate,
    repo: CurrencyRepository = Depends(get_currency_repository),
) -> ExchangeRateRecord:
    return repo.add_exchange_rate(
        base_currency=payload.base_currency,
        quote_currency=payload.quote_currency,
        rate=payload.rate,
        source=payload.source,
        rate_date=payload.rate_date,
    )
