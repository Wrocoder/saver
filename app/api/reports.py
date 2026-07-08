from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_monthly_reports_repository
from app.api.schemas import MonthlyReportResponse
from app.repositories.reports import MonthlyReportsRepository


router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/reports/monthly", response_model=MonthlyReportResponse)
def get_monthly_report(
    year: int | None = None,
    month: int | None = None,
    repo: MonthlyReportsRepository = Depends(get_monthly_reports_repository),
) -> dict:
    today = date.today()
    report_year = year or today.year
    report_month = month or today.month
    if report_year < 2000 or report_year > 2100:
        raise HTTPException(status_code=400, detail="Year must be between 2000 and 2100")
    if report_month < 1 or report_month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    return repo.build_monthly_report(report_year, report_month)
