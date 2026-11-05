"""Add persistent rate-limit buckets for authentication endpoints."""

from alembic import op
import sqlalchemy as sa


revision = "0003_rate_limit_buckets"
down_revision = "0002_user_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_buckets",
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key_hash"),
    )


def downgrade() -> None:
    op.drop_table("rate_limit_buckets")
