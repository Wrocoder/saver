import csv
import io
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AuditLogRecord,
    FinancialGoalRecord,
    GoalContributionRecord,
    ProductEventRecord,
)
from app.domain.models import DeadlineType, FinancialGoal, GoalStatus
from app.domain.models import ContributionType, GoalContribution
from app.repositories.sqlalchemy import GoalsRepository

CsvImportErrorDetail = dict[str, int | str | None]


GOAL_CSV_COLUMNS = [
    "id",
    "title",
    "category",
    "description",
    "target_amount",
    "currency",
    "current_amount",
    "desired_date",
    "priority",
    "importance",
    "deadline_type",
    "status",
    "allocation_weight",
    "product_url",
    "expected_purchase_date",
    "notes",
    "created_at",
    "updated_at",
]

GOAL_IMPORT_TEMPLATE_COLUMNS = [
    "title",
    "category",
    "description",
    "target_amount",
    "currency",
    "current_amount",
    "desired_date",
    "priority",
    "importance",
    "deadline_type",
    "allocation_weight",
    "product_url",
    "expected_purchase_date",
    "notes",
]

CONTRIBUTION_CSV_COLUMNS = [
    "id",
    "goal_id",
    "goal_title",
    "type",
    "amount",
    "currency",
    "exchange_rate_id",
    "exchange_rate",
    "amount_in_goal_currency",
    "amount_in_base_currency",
    "source",
    "comment",
    "occurred_at",
    "created_at",
    "reversed_at",
]

CONTRIBUTION_IMPORT_TEMPLATE_COLUMNS = [
    "goal_id",
    "goal_title",
    "type",
    "amount",
    "currency",
    "source",
    "comment",
    "occurred_at",
]


@dataclass(slots=True)
class CsvGoalImportResult:
    created_count: int
    skipped_count: int
    errors: list[str]
    error_details: list[CsvImportErrorDetail]
    created_goals: list[FinancialGoal]


@dataclass(slots=True)
class CsvContributionImportResult:
    created_count: int
    skipped_count: int
    errors: list[str]
    error_details: list[CsvImportErrorDetail]
    created_contributions: list[GoalContribution]


class CsvRowError(ValueError):
    def __init__(self, field: str | None, value: str | None, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.value = value
        self.message = message


class CsvDataRepository:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id
        self.goals_repo = GoalsRepository(db=db, user_id=user_id)

    def export_goals_csv(self) -> str:
        records = self.db.scalars(
            select(FinancialGoalRecord)
            .where(FinancialGoalRecord.user_id == self.user_id)
            .order_by(FinancialGoalRecord.priority.asc(), FinancialGoalRecord.created_at.asc())
        ).all()
        csv_text = write_csv(
            GOAL_CSV_COLUMNS,
            [record_to_csv_dict(record, GOAL_CSV_COLUMNS) for record in records],
        )
        self.audit_csv_action("csv_export_goals", {"rows": len(records), "format": "csv"})
        return csv_text

    def export_contributions_csv(self, from_date: date | None = None, to_date: date | None = None) -> str:
        rows = []
        statement = (
            select(GoalContributionRecord, FinancialGoalRecord.title)
            .join(FinancialGoalRecord, FinancialGoalRecord.id == GoalContributionRecord.goal_id)
            .where(GoalContributionRecord.user_id == self.user_id)
        )
        if from_date is not None:
            statement = statement.where(GoalContributionRecord.occurred_at >= from_date)
        if to_date is not None:
            statement = statement.where(GoalContributionRecord.occurred_at <= to_date)

        result = self.db.execute(
            statement.order_by(
                GoalContributionRecord.occurred_at.asc(),
                GoalContributionRecord.created_at.asc(),
            )
        )
        for contribution, goal_title in result:
            row = record_to_csv_dict(contribution, CONTRIBUTION_CSV_COLUMNS)
            row["goal_title"] = goal_title
            rows.append(row)

        csv_text = write_csv(CONTRIBUTION_CSV_COLUMNS, rows)
        self.audit_csv_action(
            "csv_export_contributions",
            {
                "rows": len(rows),
                "format": "csv",
                "from_date": from_date.isoformat() if from_date else None,
                "to_date": to_date.isoformat() if to_date else None,
            },
        )
        return csv_text

    def goals_import_template_csv(self) -> str:
        csv_text = write_csv(
            GOAL_IMPORT_TEMPLATE_COLUMNS,
            [
                {
                    "title": "Emergency fund",
                    "category": "safety",
                    "description": "Three months of essential expenses",
                    "target_amount": "3000",
                    "currency": "USD",
                    "current_amount": "500",
                    "desired_date": "2026-12-31",
                    "priority": "1",
                    "importance": "5",
                    "deadline_type": "flexible",
                    "allocation_weight": "50",
                    "product_url": "",
                    "expected_purchase_date": "",
                    "notes": "Replace this example row before importing.",
                }
            ],
        )
        self.audit_csv_action("csv_template_goals_downloaded", {"format": "csv"})
        return csv_text

    def contributions_import_template_csv(self) -> str:
        csv_text = write_csv(
            CONTRIBUTION_IMPORT_TEMPLATE_COLUMNS,
            [
                {
                    "goal_id": "",
                    "goal_title": "Emergency fund",
                    "type": "add",
                    "amount": "100",
                    "currency": "USD",
                    "source": "salary",
                    "comment": "Replace this example row before importing.",
                    "occurred_at": "2026-07-01",
                }
            ],
        )
        self.audit_csv_action("csv_template_contributions_downloaded", {"format": "csv"})
        return csv_text

    def import_goals_csv(self, csv_text: str) -> CsvGoalImportResult:
        reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
        errors: list[str] = []
        error_details: list[CsvImportErrorDetail] = []
        created_goals: list[FinancialGoal] = []
        skipped_count = 0

        if not reader.fieldnames:
            detail = csv_import_error_detail(1, None, None, "CSV header is missing.")
            return CsvGoalImportResult(
                created_count=0,
                skipped_count=0,
                errors=[format_csv_import_error(detail)],
                error_details=[detail],
                created_goals=[],
            )

        max_priority = self.db.scalar(
            select(func.coalesce(func.max(FinancialGoalRecord.priority), 0)).where(
                FinancialGoalRecord.user_id == self.user_id
            )
        )
        next_priority = int(max_priority or 0) + 1

        for row_number, raw_row in enumerate(reader, start=2):
            row = normalize_csv_row(raw_row)
            if is_blank_row(row):
                skipped_count += 1
                continue

            try:
                goal = self.row_to_goal(row=row, fallback_priority=next_priority)
            except CsvRowError as exc:
                detail = csv_import_error_detail(row_number, exc.field, exc.value, exc.message)
                error_details.append(detail)
                errors.append(format_csv_import_error(detail))
                skipped_count += 1
                continue
            except ValueError as exc:
                detail = csv_import_error_detail(row_number, None, None, str(exc))
                error_details.append(detail)
                errors.append(format_csv_import_error(detail))
                skipped_count += 1
                continue

            created_goals.append(self.goals_repo.add_goal(goal))
            next_priority += 1

        self.audit_csv_action(
            "csv_import_goals",
            {
                "created_count": len(created_goals),
                "skipped_count": skipped_count,
                "errors_count": len(errors),
                "format": "csv",
            },
        )
        return CsvGoalImportResult(
            created_count=len(created_goals),
            skipped_count=skipped_count,
            errors=errors,
            error_details=error_details,
            created_goals=created_goals,
        )

    def import_contributions_csv(self, csv_text: str) -> CsvContributionImportResult:
        reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
        errors: list[str] = []
        error_details: list[CsvImportErrorDetail] = []
        created_contributions: list[GoalContribution] = []
        skipped_count = 0

        if not reader.fieldnames:
            detail = csv_import_error_detail(1, None, None, "CSV header is missing.")
            return CsvContributionImportResult(
                created_count=0,
                skipped_count=0,
                errors=[format_csv_import_error(detail)],
                error_details=[detail],
                created_contributions=[],
            )

        for row_number, raw_row in enumerate(reader, start=2):
            row = normalize_csv_row(raw_row)
            if is_blank_row(row):
                skipped_count += 1
                continue

            try:
                contribution = self.row_to_contribution(row)
                created_contributions.append(self.goals_repo.add_contribution(contribution))
            except CsvRowError as exc:
                detail = csv_import_error_detail(row_number, exc.field, exc.value, exc.message)
                error_details.append(detail)
                errors.append(format_csv_import_error(detail))
                skipped_count += 1
            except ValueError as exc:
                detail = csv_import_error_detail(row_number, None, None, str(exc))
                error_details.append(detail)
                errors.append(format_csv_import_error(detail))
                skipped_count += 1

        self.audit_csv_action(
            "csv_import_contributions",
            {
                "created_count": len(created_contributions),
                "skipped_count": skipped_count,
                "errors_count": len(errors),
                "format": "csv",
            },
        )
        return CsvContributionImportResult(
            created_count=len(created_contributions),
            skipped_count=skipped_count,
            errors=errors,
            error_details=error_details,
            created_contributions=created_contributions,
        )

    def row_to_goal(self, row: dict[str, str], fallback_priority: int) -> FinancialGoal:
        title = value_or_none(row.get("title"))
        if title is None:
            raise CsvRowError("title", row.get("title"), "title is required")
        if len(title) > 120:
            raise CsvRowError("title", row.get("title"), "title must be 120 characters or less")

        target_amount = parse_decimal(row.get("target_amount"), "target_amount", required=True)
        if target_amount <= 0:
            raise CsvRowError(
                "target_amount",
                row.get("target_amount"),
                "target_amount must be greater than 0",
            )

        current_amount = parse_decimal(row.get("current_amount"), "current_amount") or Decimal("0")
        if current_amount < 0:
            raise CsvRowError(
                "current_amount",
                row.get("current_amount"),
                "current_amount must be greater than or equal to 0",
            )

        currency = (value_or_none(row.get("currency")) or "USD").upper()
        if len(currency) != 3:
            raise CsvRowError("currency", row.get("currency"), "currency must be a 3-letter code")

        priority = parse_int(row.get("priority"), "priority") or fallback_priority
        if priority < 1:
            raise CsvRowError("priority", row.get("priority"), "priority must be greater than or equal to 1")

        importance = parse_int(row.get("importance"), "importance") or 3
        if importance < 1 or importance > 5:
            raise CsvRowError("importance", row.get("importance"), "importance must be between 1 and 5")

        deadline_type_value = value_or_none(row.get("deadline_type")) or DeadlineType.FLEXIBLE.value
        try:
            deadline_type = DeadlineType(deadline_type_value)
        except ValueError as exc:
            raise CsvRowError(
                "deadline_type",
                row.get("deadline_type"),
                "deadline_type must be hard or flexible",
            ) from exc

        status_value = value_or_none(row.get("status")) or GoalStatus.ACTIVE.value
        try:
            status = GoalStatus(status_value)
        except ValueError as exc:
            raise CsvRowError("status", row.get("status"), "status is not supported") from exc

        allocation_weight = parse_decimal(row.get("allocation_weight"), "allocation_weight")
        if allocation_weight is not None and (allocation_weight < 0 or allocation_weight > 100):
            raise CsvRowError(
                "allocation_weight",
                row.get("allocation_weight"),
                "allocation_weight must be between 0 and 100",
            )

        return FinancialGoal(
            title=title,
            category=validate_length(row.get("category"), "category", 80),
            description=validate_length(row.get("description"), "description", 1000),
            target_amount=target_amount,
            currency=currency,
            current_amount=current_amount,
            desired_date=parse_date(row.get("desired_date"), "desired_date"),
            priority=priority,
            importance=importance,
            deadline_type=deadline_type,
            status=status,
            allocation_weight=allocation_weight,
            product_url=validate_length(row.get("product_url"), "product_url", 2048),
            expected_purchase_date=parse_date(row.get("expected_purchase_date"), "expected_purchase_date"),
            notes=validate_length(row.get("notes"), "notes", 2000),
        )

    def row_to_contribution(self, row: dict[str, str]) -> GoalContribution:
        goal_id = self.resolve_contribution_goal_id(row)

        type_value = value_or_none(row.get("type")) or ContributionType.ADD.value
        try:
            contribution_type = ContributionType(type_value)
        except ValueError as exc:
            raise CsvRowError("type", row.get("type"), "type is not supported") from exc

        amount = parse_decimal(row.get("amount"), "amount", required=True)
        if amount <= 0:
            raise CsvRowError("amount", row.get("amount"), "amount must be greater than 0")

        goal = self.goals_repo.get_goal(goal_id)
        if goal is None:
            raise CsvRowError("goal_id", row.get("goal_id"), "goal not found")

        currency = (value_or_none(row.get("currency")) or goal.currency).upper()
        if len(currency) != 3:
            raise CsvRowError("currency", row.get("currency"), "currency must be a 3-letter code")

        return GoalContribution(
            goal_id=goal_id,
            type=contribution_type,
            amount=amount,
            currency=currency,
            source=validate_length(row.get("source"), "source", 120),
            comment=validate_length(row.get("comment"), "comment", 1000),
            occurred_at=parse_date(row.get("occurred_at"), "occurred_at") or date.today(),
        )

    def resolve_contribution_goal_id(self, row: dict[str, str]) -> str:
        goal_id = value_or_none(row.get("goal_id"))
        if goal_id is not None:
            if self.goals_repo.get_goal(goal_id) is None:
                raise CsvRowError("goal_id", row.get("goal_id"), "goal_id does not match an active goal")
            return goal_id

        goal_title = value_or_none(row.get("goal_title"))
        if goal_title is None:
            raise CsvRowError(
                "goal_id/goal_title",
                row.get("goal_id") or row.get("goal_title"),
                "goal_id or goal_title is required",
            )

        matches = [
            goal
            for goal in self.goals_repo.list_goals()
            if goal.title.casefold() == goal_title.casefold()
        ]
        if not matches:
            raise CsvRowError("goal_title", row.get("goal_title"), "goal_title does not match an active goal")
        if len(matches) > 1:
            raise CsvRowError("goal_title", row.get("goal_title"), "goal_title matches multiple goals; use goal_id")
        return matches[0].id

    def audit_csv_action(self, action: str, payload: dict[str, Any]) -> None:
        self.db.add(
            AuditLogRecord(
                actor_user_id=self.user_id,
                entity_type="user",
                entity_id=self.user_id,
                action=action,
                before_json=None,
                after_json=payload,
            )
        )
        self.db.add(
            ProductEventRecord(
                user_id=self.user_id,
                name=action,
                source="api",
                properties=payload,
            )
        )
        self.db.commit()


def write_csv(columns: list[str], rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: csv_cell(row.get(column)) for column in columns})
    return output.getvalue()


def record_to_csv_dict(record: Any, columns: list[str]) -> dict[str, Any]:
    return {column: getattr(record, column, None) for column in columns}


def csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


def normalize_csv_row(row: dict[str, str | None]) -> dict[str, str]:
    return {
        (key or "").strip(): (value or "").strip()
        for key, value in row.items()
        if key is not None
    }


def is_blank_row(row: dict[str, str]) -> bool:
    return not any(value for value in row.values())


def value_or_none(value: str | None) -> str | None:
    stripped = value.strip() if value else ""
    return stripped or None


def csv_import_error_detail(
    row_number: int | None,
    field: str | None,
    value: str | None,
    message: str,
) -> CsvImportErrorDetail:
    return {
        "row_number": row_number,
        "field": field,
        "value": value,
        "message": message,
    }


def format_csv_import_error(detail: CsvImportErrorDetail) -> str:
    row_number = detail.get("row_number")
    field = detail.get("field")
    value = detail.get("value")
    message = detail["message"]

    parts = [f"Row {row_number}" if row_number is not None else "CSV"]
    if field:
        parts.append(f"field {field}")
    if value is not None:
        parts.append(f'value "{value}"')
    return f"{' · '.join(parts)}: {message}"


def validate_length(value: str | None, field: str, max_length: int) -> str | None:
    result = value_or_none(value)
    if result is not None and len(result) > max_length:
        raise CsvRowError(field, value, f"{field} must be {max_length} characters or less")
    return result


def parse_decimal(value: str | None, field: str, required: bool = False) -> Decimal | None:
    raw = value_or_none(value)
    if raw is None:
        if required:
            raise CsvRowError(field, value, f"{field} is required")
        return None
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise CsvRowError(field, value, f"{field} must be a decimal number") from exc


def parse_int(value: str | None, field: str) -> int | None:
    raw = value_or_none(value)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise CsvRowError(field, value, f"{field} must be an integer") from exc


def parse_date(value: str | None, field: str) -> date | None:
    raw = value_or_none(value)
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise CsvRowError(field, value, f"{field} must use YYYY-MM-DD format") from exc
