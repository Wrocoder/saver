"""recurring rules

Revision ID: 0007_recurring_rules
Revises: 0006_notifications
Create Date: 2026-07-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0007_recurring_rules"
down_revision: str | None = "0006_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recurring_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("goal_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("frequency", sa.String(length=30), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("next_run_on", sa.Date(), nullable=True),
        sa.Column("last_run_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["financial_goals.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recurring_rules_goal_id"), "recurring_rules", ["goal_id"], unique=False)
    op.create_index(op.f("ix_recurring_rules_is_active"), "recurring_rules", ["is_active"], unique=False)
    op.create_index(op.f("ix_recurring_rules_user_id"), "recurring_rules", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_recurring_rules_user_id"), table_name="recurring_rules")
    op.drop_index(op.f("ix_recurring_rules_is_active"), table_name="recurring_rules")
    op.drop_index(op.f("ix_recurring_rules_goal_id"), table_name="recurring_rules")
    op.drop_table("recurring_rules")
