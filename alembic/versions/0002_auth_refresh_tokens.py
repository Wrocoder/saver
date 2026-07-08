"""auth refresh tokens

Revision ID: 0002_auth_refresh_tokens
Revises: 0001_initial_schema
Create Date: 2026-07-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002_auth_refresh_tokens"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_refresh_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_refresh_tokens_expires_at"), "auth_refresh_tokens", ["expires_at"], unique=False)
    op.create_index(op.f("ix_auth_refresh_tokens_token_hash"), "auth_refresh_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_auth_refresh_tokens_user_id"), "auth_refresh_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_refresh_tokens_user_id"), table_name="auth_refresh_tokens")
    op.drop_index(op.f("ix_auth_refresh_tokens_token_hash"), table_name="auth_refresh_tokens")
    op.drop_index(op.f("ix_auth_refresh_tokens_expires_at"), table_name="auth_refresh_tokens")
    op.drop_table("auth_refresh_tokens")
