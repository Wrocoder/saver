"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("timezone", sa.String(length=80), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("income_type", sa.String(length=30), nullable=True),
        sa.Column("average_monthly_income", sa.Numeric(18, 4), nullable=True),
        sa.Column("mandatory_monthly_expenses", sa.Numeric(18, 4), nullable=True),
        sa.Column("monthly_available_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("desired_min_balance", sa.Numeric(18, 4), nullable=True),
        sa.Column("notification_settings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "financial_goals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("current_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("desired_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("deadline_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("allocation_weight", sa.Numeric(8, 4), nullable=True),
        sa.Column("product_url", sa.String(length=2048), nullable=True),
        sa.Column("expected_purchase_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_financial_goals_user_id"), "financial_goals", ["user_id"], unique=False)

    op.create_table(
        "goal_contributions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("goal_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["goal_id"], ["financial_goals.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_goal_contributions_goal_id"), "goal_contributions", ["goal_id"], unique=False)
    op.create_index(op.f("ix_goal_contributions_user_id"), "goal_contributions", ["user_id"], unique=False)

    op.create_table(
        "allocation_strategies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("fixed_amounts", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_allocation_strategies_user_id"), "allocation_strategies", ["user_id"], unique=True)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_log_actor_user_id"), "audit_log", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_audit_log_entity_id"), "audit_log", ["entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_log_entity_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_user_id"), table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index(op.f("ix_allocation_strategies_user_id"), table_name="allocation_strategies")
    op.drop_table("allocation_strategies")
    op.drop_index(op.f("ix_goal_contributions_user_id"), table_name="goal_contributions")
    op.drop_index(op.f("ix_goal_contributions_goal_id"), table_name="goal_contributions")
    op.drop_table("goal_contributions")
    op.drop_index(op.f("ix_financial_goals_user_id"), table_name="financial_goals")
    op.drop_table("financial_goals")
    op.drop_table("user_profiles")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
