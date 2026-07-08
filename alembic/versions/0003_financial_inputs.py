"""financial inputs

Revision ID: 0003_financial_inputs
Revises: 0002_auth_refresh_tokens
Create Date: 2026-07-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003_financial_inputs"
down_revision: str | None = "0002_auth_refresh_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "incomes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("frequency", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("is_recurring", sa.Boolean(), nullable=False),
        sa.Column("received_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incomes_user_id"), "incomes", ["user_id"], unique=False)

    op.create_table(
        "expenses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("frequency", sa.String(length=30), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("is_recurring", sa.Boolean(), nullable=False),
        sa.Column("occurred_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expenses_user_id"), "expenses", ["user_id"], unique=False)

    op.create_table(
        "debts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("creditor", sa.String(length=120), nullable=True),
        sa.Column("balance", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("interest_rate", sa.Numeric(8, 4), nullable=True),
        sa.Column("min_monthly_payment", sa.Numeric(18, 4), nullable=False),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_debts_user_id"), "debts", ["user_id"], unique=False)

    op.create_table(
        "emergency_funds",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("target_months", sa.Integer(), nullable=False),
        sa.Column("target_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("current_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("monthly_contribution", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_emergency_funds_user_id"), "emergency_funds", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_emergency_funds_user_id"), table_name="emergency_funds")
    op.drop_table("emergency_funds")
    op.drop_index(op.f("ix_debts_user_id"), table_name="debts")
    op.drop_table("debts")
    op.drop_index(op.f("ix_expenses_user_id"), table_name="expenses")
    op.drop_table("expenses")
    op.drop_index(op.f("ix_incomes_user_id"), table_name="incomes")
    op.drop_table("incomes")
