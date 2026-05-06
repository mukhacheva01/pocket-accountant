"""admin metrics and user activity

Revision ID: 20260414_0004
Revises: 20260405_0003
Create Date: 2026-04-14 16:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260414_0004"
down_revision = "20260405_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("last_command", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("reactivated_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "user_activity",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_index("ix_user_activity_user_id", "user_activity", ["user_id"])
    op.create_index("ix_user_activity_created_at", "user_activity", ["created_at"])
    op.create_index("ix_user_activity_event_type", "user_activity", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_user_activity_event_type", table_name="user_activity")
    op.drop_index("ix_user_activity_created_at", table_name="user_activity")
    op.drop_index("ix_user_activity_user_id", table_name="user_activity")
    op.drop_table("user_activity")
    op.drop_column("users", "reactivated_at")
    op.drop_column("users", "deactivated_at")
    op.drop_column("users", "last_command")
    op.drop_column("users", "last_seen_at")
