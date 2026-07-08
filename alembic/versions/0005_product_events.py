"""product events

Revision ID: 0005_product_events
Revises: 0004_currencies_and_conversion_fields
Create Date: 2026-07-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0005_product_events"
down_revision: str | None = "0004_currencies_and_conversion_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_events_name"), "product_events", ["name"], unique=False)
    op.create_index(op.f("ix_product_events_user_id"), "product_events", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_product_events_user_id"), table_name="product_events")
    op.drop_index(op.f("ix_product_events_name"), table_name="product_events")
    op.drop_table("product_events")
