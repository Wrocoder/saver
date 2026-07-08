"""goal price history

Revision ID: 0008_goal_price_history
Revises: 0007_recurring_rules
Create Date: 2026-07-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0008_goal_price_history"
down_revision: str | None = "0007_recurring_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goal_price_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("goal_id", sa.String(length=36), nullable=False),
        sa.Column("previous_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("new_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["financial_goals.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_goal_price_history_goal_id"), "goal_price_history", ["goal_id"], unique=False)
    op.create_index(op.f("ix_goal_price_history_user_id"), "goal_price_history", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_goal_price_history_user_id"), table_name="goal_price_history")
    op.drop_index(op.f("ix_goal_price_history_goal_id"), table_name="goal_price_history")
    op.drop_table("goal_price_history")
