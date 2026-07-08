from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLogRecord, NotificationRecord, UserProfileRecord
from app.domain.planning import FinancialPlanResult, GoalProjection


ALLOWED_NOTIFICATION_FREQUENCIES = {"instant", "daily", "weekly", "monthly"}
BOOLEAN_NOTIFICATION_SETTINGS = {
    "in_app_enabled",
    "plan_warnings",
    "milestone_updates",
    "monthly_reminders",
    "email_enabled",
}
FREQUENCY_NOTIFICATION_SETTINGS = {"in_app_frequency", "email_frequency"}

DEFAULT_NOTIFICATION_SETTINGS: dict[str, Any] = {
    "in_app_enabled": True,
    "plan_warnings": True,
    "milestone_updates": True,
    "monthly_reminders": True,
    "email_enabled": False,
    "in_app_frequency": "daily",
    "email_frequency": "weekly",
}


class NotificationsRepository:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def list_notifications(self, status: str | None = None, limit: int = 50) -> list[NotificationRecord]:
        query = select(NotificationRecord).where(NotificationRecord.user_id == self.user_id)
        if status is not None:
            query = query.where(NotificationRecord.status == status)
        query = query.order_by(NotificationRecord.created_at.desc()).limit(limit)
        return list(self.db.scalars(query))

    def create_notification(
        self,
        notification_type: str,
        title: str,
        body: str,
        severity: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> NotificationRecord | None:
        metadata = metadata or {}
        dedupe_key = str(metadata.get("dedupe_key") or "")
        if dedupe_key and self.has_open_notification(notification_type, dedupe_key):
            return None

        record = NotificationRecord(
            user_id=self.user_id,
            type=notification_type,
            title=title,
            body=body,
            severity=severity,
            metadata_json=metadata,
        )
        self.db.add(record)
        self.db.flush()
        self.audit("notification", record.id, "create", None, notification_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def mark_read(self, notification_id: str) -> NotificationRecord | None:
        record = self.get_notification_record(notification_id)
        if record is None:
            return None

        before = notification_snapshot(record)
        record.status = "read"
        record.read_at = datetime.now(UTC)
        self.audit("notification", record.id, "read", before, notification_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def dismiss(self, notification_id: str) -> NotificationRecord | None:
        record = self.get_notification_record(notification_id)
        if record is None:
            return None

        before = notification_snapshot(record)
        record.status = "dismissed"
        if record.read_at is None:
            record.read_at = datetime.now(UTC)
        self.audit("notification", record.id, "dismiss", before, notification_snapshot(record))
        self.db.commit()
        self.db.refresh(record)
        return record

    def generate_from_plan(self, plan: FinancialPlanResult) -> list[NotificationRecord]:
        settings = self.get_settings()
        if not settings["in_app_enabled"]:
            return []

        candidates: list[NotificationCandidate] = []

        if settings["plan_warnings"]:
            for index, conflict in enumerate(plan.conflicts):
                candidates.append(
                    NotificationCandidate(
                        notification_type="plan_conflict",
                        title="Plan needs attention",
                        body=conflict,
                        severity="warning",
                        metadata={"dedupe_key": f"plan_conflict:{index}:{conflict}"},
                    )
                )

            for goal in plan.goals:
                if goal.status in {"at_risk", "not_funded", "late_but_adjustable"}:
                    candidates.append(goal_warning_candidate(goal))

        if settings["milestone_updates"]:
            for goal in plan.goals:
                if 75 <= int(goal.progress_percent) < 100:
                    candidates.append(
                        NotificationCandidate(
                            notification_type="goal_milestone",
                            title=f"{goal.title} is past 75%",
                            body=f"{goal.remaining_amount} {goal.currency} remains before the target amount.",
                            severity="success",
                            metadata={"goal_id": goal.goal_id, "dedupe_key": f"goal_milestone_75:{goal.goal_id}"},
                        )
                    )

        if settings["monthly_reminders"]:
            funded_goal = next((goal for goal in plan.goals if goal.allocated_first_month > 0), None)
            if funded_goal is not None:
                candidates.append(
                    NotificationCandidate(
                        notification_type="planned_contribution",
                        title="Planned contribution",
                        body=(
                            f"Add {funded_goal.allocated_first_month} {funded_goal.currency} "
                            f"to '{funded_goal.title}' this month."
                        ),
                        severity="info",
                        metadata={
                            "goal_id": funded_goal.goal_id,
                            "dedupe_key": f"planned_contribution:{plan.generated_at:%Y-%m}:{funded_goal.goal_id}",
                        },
                    )
                )

        created: list[NotificationRecord] = []
        for candidate in candidates:
            record = self.create_notification(
                notification_type=candidate.notification_type,
                title=candidate.title,
                body=candidate.body,
                severity=candidate.severity,
                metadata=candidate.metadata,
            )
            if record is not None:
                created.append(record)
        return created

    def run_scheduler_from_plan(
        self,
        plan: FinancialPlanResult,
        now: datetime | None = None,
    ) -> list[NotificationRecord]:
        now = now or datetime.now(UTC)
        if not self.scheduler_due(now):
            return []

        created = self.generate_from_plan(plan)
        self.record_scheduler_run(created_count=len(created), now=now)
        return created

    def scheduler_due(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        settings = self.get_settings()
        period_start, period_end = scheduler_period(now, settings["in_app_frequency"])
        marker_id = self.db.scalar(
            select(AuditLogRecord.id)
            .where(
                AuditLogRecord.actor_user_id == self.user_id,
                AuditLogRecord.entity_type == "notification_scheduler",
                AuditLogRecord.action == "run",
                AuditLogRecord.created_at >= period_start,
                AuditLogRecord.created_at < period_end,
            )
            .limit(1)
        )
        return marker_id is None

    def record_scheduler_run(
        self,
        created_count: int,
        now: datetime | None = None,
        skipped_reason: str | None = None,
    ) -> None:
        now = now or datetime.now(UTC)
        self.audit(
            "notification_scheduler",
            self.user_id,
            "run",
            None,
            {
                "run_date": now.date().isoformat(),
                "frequency": self.get_settings()["in_app_frequency"],
                "created_count": created_count,
                "skipped_reason": skipped_reason,
            },
        )
        self.db.commit()

    def get_settings(self) -> dict[str, Any]:
        profile = self.get_or_create_profile()
        current = profile.notification_settings or {}
        settings = dict(DEFAULT_NOTIFICATION_SETTINGS)
        for key in BOOLEAN_NOTIFICATION_SETTINGS:
            if key in current:
                settings[key] = bool(current[key])
        for key in FREQUENCY_NOTIFICATION_SETTINGS:
            value = str(current.get(key) or "").lower()
            if value in ALLOWED_NOTIFICATION_FREQUENCIES:
                settings[key] = value
        return settings

    def update_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        profile = self.get_or_create_profile()
        before = dict(profile.notification_settings or {})
        next_settings = self.get_settings()
        for key, value in updates.items():
            if key in BOOLEAN_NOTIFICATION_SETTINGS:
                next_settings[key] = bool(value)
            elif key in FREQUENCY_NOTIFICATION_SETTINGS:
                frequency = str(value).lower()
                if frequency in ALLOWED_NOTIFICATION_FREQUENCIES:
                    next_settings[key] = frequency
        profile.notification_settings = next_settings
        self.audit(
            "notification_settings",
            self.user_id,
            "update",
            before,
            next_settings,
        )
        self.db.commit()
        return next_settings

    def has_open_notification(self, notification_type: str, dedupe_key: str) -> bool:
        records = self.db.scalars(
            select(NotificationRecord).where(
                NotificationRecord.user_id == self.user_id,
                NotificationRecord.type == notification_type,
                NotificationRecord.status.in_(["unread", "read"]),
            )
        )
        return any(record.metadata_json.get("dedupe_key") == dedupe_key for record in records)

    def get_notification_record(self, notification_id: str) -> NotificationRecord | None:
        return self.db.scalar(
            select(NotificationRecord).where(
                NotificationRecord.id == notification_id,
                NotificationRecord.user_id == self.user_id,
            )
        )

    def get_or_create_profile(self) -> UserProfileRecord:
        profile = self.db.get(UserProfileRecord, self.user_id)
        if profile is not None:
            return profile
        profile = UserProfileRecord(user_id=self.user_id)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

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


class NotificationCandidate:
    def __init__(
        self,
        notification_type: str,
        title: str,
        body: str,
        severity: str,
        metadata: dict[str, Any],
    ) -> None:
        self.notification_type = notification_type
        self.title = title
        self.body = body
        self.severity = severity
        self.metadata = metadata


def goal_warning_candidate(goal: GoalProjection) -> NotificationCandidate:
    title = "Goal needs a decision"
    if goal.status == "at_risk":
        title = f"{goal.title} is at risk"
    elif goal.status == "not_funded":
        title = f"{goal.title} is not funded"

    return NotificationCandidate(
        notification_type="goal_plan_warning",
        title=title,
        body=goal.explanation,
        severity="warning",
        metadata={
            "goal_id": goal.goal_id,
            "status": goal.status,
            "dedupe_key": f"goal_plan_warning:{goal.goal_id}:{goal.status}",
        },
    )


def scheduler_period(now: datetime, frequency: str) -> tuple[datetime, datetime]:
    day_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=UTC)
    if frequency == "weekly":
        week_start = day_start - timedelta(days=day_start.weekday())
        return week_start, week_start + timedelta(days=7)
    if frequency == "monthly":
        month_start = day_start.replace(day=1)
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)
        return month_start, next_month
    return day_start, day_start + timedelta(days=1)


def notification_snapshot(record: NotificationRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "type": record.type,
        "title": record.title,
        "severity": record.severity,
        "status": record.status,
        "metadata_json": record.metadata_json,
    }
