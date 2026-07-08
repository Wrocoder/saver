from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ProductEventRecord

KEY_METRIC_EVENTS = {
    "goals_created": ["goal_created"],
    "contributions_added": ["contribution_added"],
    "scenarios_run": ["scenario_run"],
    "priority_changes": ["priority_changed"],
    "csv_imports": [
        "csv_goals_imported",
        "csv_contributions_imported",
        "csv_import_goals",
        "csv_import_contributions",
    ],
    "exports": [
        "data_export_downloaded",
        "data_exported",
        "csv_goals_exported",
        "csv_contributions_exported",
        "csv_contributions_period_exported",
        "csv_export_goals",
        "csv_export_contributions",
    ],
}


class AnalyticsRepository:
    def __init__(self, db: Session, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def record_event(
        self,
        name: str,
        properties: dict[str, Any] | None = None,
        source: str = "web",
    ) -> ProductEventRecord:
        record = ProductEventRecord(
            user_id=self.user_id,
            name=name,
            source=source,
            properties=sanitize_properties(properties or {}),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_events(self, limit: int = 100) -> list[ProductEventRecord]:
        return list(
            self.db.scalars(
                select(ProductEventRecord)
                .where(ProductEventRecord.user_id == self.user_id)
                .order_by(ProductEventRecord.created_at.desc())
                .limit(limit)
            )
        )

    def summary(self, now: datetime | None = None) -> dict[str, Any]:
        current_time = normalize_datetime(now or datetime.now(UTC))
        events = list(
            self.db.scalars(
                select(ProductEventRecord)
                .where(ProductEventRecord.user_id == self.user_id)
                .order_by(ProductEventRecord.created_at.desc())
            )
        )
        counter = Counter(event.name for event in events)
        events_last_7_days = count_since(events, current_time, days=7)
        events_last_30_days = count_since(events, current_time, days=30)
        active_days_last_30 = {
            normalize_datetime(event.created_at).date()
            for event in events
            if normalize_datetime(event.created_at) >= current_time - timedelta(days=30)
        }

        return {
            "total_events": len(events),
            "events_last_7_days": events_last_7_days,
            "events_last_30_days": events_last_30_days,
            "active_days_last_30": len(active_days_last_30),
            "last_event_at": events[0].created_at if events else None,
            "key_metrics": {
                name: sum(counter[event_name] for event_name in event_names)
                for name, event_names in KEY_METRIC_EVENTS.items()
            },
            "event_counts": [
                {"name": name, "count": count}
                for name, count in counter.most_common()
            ],
            "recent_events": events[:10],
        }


def sanitize_properties(properties: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in properties.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized


def normalize_datetime(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def count_since(events: list[ProductEventRecord], now: datetime, days: int) -> int:
    cutoff = now - timedelta(days=days)
    return sum(1 for event in events if normalize_datetime(event.created_at) >= cutoff)
