"""currencies and conversion fields

Revision ID: 0004_currencies_and_conversion_fields
Revises: 0003_financial_inputs
Create Date: 2026-07-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0004_currencies_and_conversion_fields"
down_revision: str | None = "0003_financial_inputs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "currencies",
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("symbol", sa.String(length=8), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("decimals", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("quote_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(20, 10), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exchange_rates_base_currency"), "exchange_rates", ["base_currency"], unique=False)
    op.create_index(op.f("ix_exchange_rates_quote_currency"), "exchange_rates", ["quote_currency"], unique=False)
    op.create_index(op.f("ix_exchange_rates_rate_date"), "exchange_rates", ["rate_date"], unique=False)

    op.add_column("goal_contributions", sa.Column("exchange_rate_id", sa.String(length=36), nullable=True))
    op.add_column("goal_contributions", sa.Column("exchange_rate", sa.Numeric(20, 10), nullable=True))
    op.add_column("goal_contributions", sa.Column("amount_in_goal_currency", sa.Numeric(18, 4), nullable=True))
    op.add_column("goal_contributions", sa.Column("amount_in_base_currency", sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("goal_contributions", "amount_in_base_currency")
    op.drop_column("goal_contributions", "amount_in_goal_currency")
    op.drop_column("goal_contributions", "exchange_rate")
    op.drop_column("goal_contributions", "exchange_rate_id")
    op.drop_index(op.f("ix_exchange_rates_rate_date"), table_name="exchange_rates")
    op.drop_index(op.f("ix_exchange_rates_quote_currency"), table_name="exchange_rates")
    op.drop_index(op.f("ix_exchange_rates_base_currency"), table_name="exchange_rates")
    op.drop_table("exchange_rates")
    op.drop_table("currencies")
