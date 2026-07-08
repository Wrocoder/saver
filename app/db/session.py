from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base


def sqlite_connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


engine = create_engine(
    settings.database_url,
    connect_args=sqlite_connect_args(settings.database_url),
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema_updates()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_schema_updates() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "goal_contributions" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("goal_contributions")
    }
    columns_to_add = {
        "exchange_rate_id": "VARCHAR(36)",
        "exchange_rate": "NUMERIC(20, 10)",
        "amount_in_goal_currency": "NUMERIC(18, 4)",
        "amount_in_base_currency": "NUMERIC(18, 4)",
    }

    with engine.begin() as connection:
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE goal_contributions ADD COLUMN {column_name} {column_type}")
                )
