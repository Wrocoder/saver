from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import get_analytics_repository, get_csv_repository, get_export_repository
from app.api.schemas import (
    AnalyticsEventCreate,
    AnalyticsEventResponse,
    AnalyticsSummaryResponse,
    CsvContributionImportResponse,
    CsvGoalImportResponse,
    CsvImportRequest,
)
from app.db.models import ProductEventRecord
from app.repositories.analytics import AnalyticsRepository
from app.repositories.csv_io import CsvContributionImportResult, CsvDataRepository, CsvGoalImportResult
from app.repositories.export import UserExportRepository


router = APIRouter(prefix="/api", tags=["analytics"])


@router.post(
    "/analytics/events",
    response_model=AnalyticsEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analytics_event(
    payload: AnalyticsEventCreate,
    repo: AnalyticsRepository = Depends(get_analytics_repository),
) -> ProductEventRecord:
    return repo.record_event(
        name=payload.name,
        properties=payload.properties,
        source=payload.source,
    )


@router.get("/analytics/events", response_model=list[AnalyticsEventResponse])
def list_analytics_events(
    limit: int = 100,
    repo: AnalyticsRepository = Depends(get_analytics_repository),
) -> list[ProductEventRecord]:
    return repo.list_events(limit=min(max(limit, 1), 500))


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(
    repo: AnalyticsRepository = Depends(get_analytics_repository),
) -> dict[str, Any]:
    return repo.summary()


@router.get("/export/user-data")
def export_user_data(repo: UserExportRepository = Depends(get_export_repository)) -> Response:
    payload: dict[str, Any] = repo.build_export()
    return Response(
        content=to_pretty_json(payload),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="money-saver-export.json"'},
    )


@router.get("/export/goals.csv")
def export_goals_csv(repo: CsvDataRepository = Depends(get_csv_repository)) -> Response:
    return Response(
        content=repo.export_goals_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="money-saver-goals.csv"'},
    )


@router.get("/export/contributions.csv")
def export_contributions_csv(
    from_date: date | None = None,
    to_date: date | None = None,
    repo: CsvDataRepository = Depends(get_csv_repository),
) -> Response:
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date must be earlier than or equal to to_date")
    return Response(
        content=repo.export_contributions_csv(from_date=from_date, to_date=to_date),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="money-saver-contributions.csv"'},
    )


@router.get("/import/goals-template.csv")
def goals_import_template_csv(repo: CsvDataRepository = Depends(get_csv_repository)) -> Response:
    return Response(
        content=repo.goals_import_template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="money-saver-goals-import-template.csv"'},
    )


@router.get("/import/contributions-template.csv")
def contributions_import_template_csv(repo: CsvDataRepository = Depends(get_csv_repository)) -> Response:
    return Response(
        content=repo.contributions_import_template_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="money-saver-contributions-import-template.csv"'
        },
    )


@router.post("/import/goals.csv", response_model=CsvGoalImportResponse)
def import_goals_csv(
    payload: CsvImportRequest,
    repo: CsvDataRepository = Depends(get_csv_repository),
) -> CsvGoalImportResult:
    return repo.import_goals_csv(payload.csv_text)


@router.post("/import/contributions.csv", response_model=CsvContributionImportResponse)
def import_contributions_csv(
    payload: CsvImportRequest,
    repo: CsvDataRepository = Depends(get_csv_repository),
) -> CsvContributionImportResult:
    return repo.import_contributions_csv(payload.csv_text)


def to_pretty_json(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2)
