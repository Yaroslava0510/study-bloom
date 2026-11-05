"""Add persistent user profile preferences."""

from alembic import op
import sqlalchemy as sa


revision = "0004_user_profiles"
down_revision = "0003_rate_limit_buckets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False, server_default=""),
        sa.Column("birthday", sa.Date(), nullable=True),
        sa.Column("interests", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("theme", sa.String(length=24), nullable=False, server_default="lavender"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Europe/Moscow"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_profiles")
