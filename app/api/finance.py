from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_finance_repository
from app.api.schemas import (
    DebtCreate,
    DebtResponse,
    DebtUpdate,
    EmergencyFundResponse,
    EmergencyFundUpsert,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
    FinancialSummaryResponse,
    IncomeCreate,
    IncomeResponse,
    IncomeUpdate,
    ProfileResponse,
    ProfileUpdate,
)
from app.db.models import (
    DebtRecord,
    EmergencyFundRecord,
    ExpenseRecord,
    IncomeRecord,
    UserProfileRecord,
)
from app.repositories.finance import FinanceRepository


router = APIRouter(prefix="/api", tags=["finance"])


@router.get("/me/profile", response_model=ProfileResponse)
def get_profile(repo: FinanceRepository = Depends(get_finance_repository)) -> UserProfileRecord:
    return repo.get_profile()


@router.patch("/me/profile", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdate,
    repo: FinanceRepository = Depends(get_finance_repository),
) -> UserProfileRecord:
    return repo.update_profile(payload.model_dump(exclude_unset=True))


@router.get("/incomes", response_model=list[IncomeResponse])
def list_incomes(repo: FinanceRepository = Depends(get_finance_repository)) -> list[IncomeRecord]:
    return repo.list_incomes()


@router.post("/incomes", response_model=IncomeResponse, status_code=status.HTTP_201_CREATED)
def create_income(
    payload: IncomeCreate,
    repo: FinanceRepository = Depends(get_finance_repository),
) -> IncomeRecord:
    return repo.add_income(
        amount=payload.amount,
        currency=payload.currency,
        frequency=payload.frequency.value,
        source=payload.source,
        is_recurring=payload.is_recurring,
        received_at=payload.received_at,
    )


@router.patch("/incomes/{income_id}", response_model=IncomeResponse)
def update_income(
    income_id: str,
    payload: IncomeUpdate,
    repo: FinanceRepository = Depends(get_finance_repository),
) -> IncomeRecord:
    record = repo.update_income(income_id, payload.model_dump(exclude_unset=True))
    if record is None:
        raise HTTPException(status_code=404, detail="Income not found")
    return record


@router.delete("/incomes/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income(
    income_id: str,
    repo: FinanceRepository = Depends(get_finance_repository),
) -> None:
    if not repo.delete_income(income_id):
        raise HTTPException(status_code=404, detail="Income not found")


@router.get("/expenses", response_model=list[ExpenseResponse])
def list_expenses(repo: FinanceRepository = Depends(get_finance_repository)) -> list[ExpenseRecord]:
    return repo.list_expenses()


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    repo: FinanceRepository = Depends(get_finance_repository),
) -> ExpenseRecord:
    return repo.add_expense(
        amount=payload.amount,
        currency=payload.currency,
        category=payload.category,
        frequency=payload.frequency.value,
        is_mandatory=payload.is_mandatory,
        is_recurring=payload.is_recurring,
        occurred_at=payload.occurred_at,
    )


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: str,
    payload: ExpenseUpdate,
    repo: FinanceRepository = Depends(get_finance_repository),
) -> ExpenseRecord:
    record = repo.update_expense(expense_id, payload.model_dump(exclude_unset=True))
    if record is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return record


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: str,
    repo: FinanceRepository = Depends(get_finance_repository),
) -> None:
    if not repo.delete_expense(expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")


@router.get("/debts", response_model=list[DebtResponse])
def list_debts(repo: FinanceRepository = Depends(get_finance_repository)) -> list[DebtRecord]:
    return repo.list_debts()


@router.post("/debts", response_model=DebtResponse, status_code=status.HTTP_201_CREATED)
def create_debt(
    payload: DebtCreate,
    repo: FinanceRepository = Depends(get_finance_repository),
) -> DebtRecord:
    return repo.add_debt(
        debt_type=payload.type.value,
        creditor=payload.creditor,
        balance=payload.balance,
        currency=payload.currency,
        interest_rate=payload.interest_rate,
        min_monthly_payment=payload.min_monthly_payment,
        due_day=payload.due_day,
        status=payload.status.value,
    )


@router.patch("/debts/{debt_id}", response_model=DebtResponse)
def update_debt(
    debt_id: str,
    payload: DebtUpdate,
    repo: FinanceRepository = Depends(get_finance_repository),
) -> DebtRecord:
    record = repo.update_debt(debt_id, payload.model_dump(exclude_unset=True))
    if record is None:
        raise HTTPException(status_code=404, detail="Debt not found")
    return record


@router.delete("/debts/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_debt(
    debt_id: str,
    repo: FinanceRepository = Depends(get_finance_repository),
) -> None:
    if not repo.delete_debt(debt_id):
        raise HTTPException(status_code=404, detail="Debt not found")


@router.get("/emergency-fund", response_model=EmergencyFundResponse)
def get_emergency_fund(
    repo: FinanceRepository = Depends(get_finance_repository),
) -> EmergencyFundRecord:
    record = repo.get_emergency_fund()
    if record is None:
        raise HTTPException(status_code=404, detail="Emergency fund is not configured")
    return record


@router.put("/emergency-fund", response_model=EmergencyFundResponse)
def upsert_emergency_fund(
    payload: EmergencyFundUpsert,
    repo: FinanceRepository = Depends(get_finance_repository),
) -> EmergencyFundRecord:
    return repo.upsert_emergency_fund(
        target_months=payload.target_months,
        target_amount=payload.target_amount,
        current_amount=payload.current_amount,
        monthly_contribution=payload.monthly_contribution,
        currency=payload.currency,
    )


@router.get("/financial-summary", response_model=FinancialSummaryResponse)
def get_financial_summary(
    repo: FinanceRepository = Depends(get_finance_repository),
) -> FinancialSummaryResponse:
    return FinancialSummaryResponse(**asdict(repo.build_summary()))
