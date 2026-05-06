"""marketplace connections

Revision ID: 20260310_0002
Revises: 20260306_0001
Create Date: 2026-03-10 14:10:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260310_0002"
down_revision = "20260306_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="ozon"),
        sa.Column("seller_id", sa.String(length=128), nullable=False),
        sa.Column("api_key_secret", sa.Text(), nullable=False),
        sa.Column("api_key_masked", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("status_message", sa.Text(), nullable=True),
        sa.Column("sync_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("synced_cards", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("synced_orders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("synced_stocks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sync_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_marketplace_connections_user_id"),
    )


def downgrade() -> None:
    op.drop_table("marketplace_connections")
