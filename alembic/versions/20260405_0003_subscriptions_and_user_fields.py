"""Add subscriptions, payments tables and user fields for AI limits and referrals.

Revision ID: 20260405_0003
Revises: 20260310_0002
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = "20260405_0003"
down_revision = "20260310_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ai_requests_today", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("ai_requests_date", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("referred_by", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("referral_bonus_requests", sa.Integer(), nullable=False, server_default="0"))

    op.execute("CREATE TYPE subscriptionplan AS ENUM ('free', 'basic', 'pro', 'annual')")
    op.execute("CREATE TYPE paymentstatus AS ENUM ('pending', 'completed', 'failed', 'refunded')")

    op.execute("""
        CREATE TABLE subscriptions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
            plan subscriptionplan NOT NULL DEFAULT 'free',
            started_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            auto_renew BOOLEAN NOT NULL DEFAULT false,
            ai_requests_limit INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE payments (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            amount_stars INTEGER NOT NULL,
            plan subscriptionplan NOT NULL,
            status paymentstatus NOT NULL DEFAULT 'pending',
            telegram_payment_id VARCHAR(256),
            provider_payment_id VARCHAR(256),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX ix_payments_user_id ON payments(user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payments")
    op.execute("DROP TABLE IF EXISTS subscriptions")
    op.drop_column("users", "referral_bonus_requests")
    op.drop_column("users", "referred_by")
    op.drop_column("users", "ai_requests_date")
    op.drop_column("users", "ai_requests_today")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS subscriptionplan")
