"""initial schema

Revision ID: 20260306_0001
Revises:
Create Date: 2026-03-06 13:55:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260306_0001"
down_revision = None
branch_labels = None
depends_on = None


entity_type_enum = postgresql.ENUM("ip", "ooo", "self_employed", name="entitytype", create_type=False)
tax_regime_enum = postgresql.ENUM(
    "usn_income",
    "usn_income_expense",
    "osno",
    "npd",
    name="taxregime",
    create_type=False,
)
event_category_enum = postgresql.ENUM(
    "tax",
    "contribution",
    "declaration",
    "notice",
    "report",
    "hr",
    "employee",
    "marketplace",
    "other",
    name="eventcategory",
    create_type=False,
)
event_status_enum = postgresql.ENUM("pending", "completed", "dismissed", "overdue", name="eventstatus", create_type=False)
reminder_type_enum = postgresql.ENUM(
    "days_7",
    "days_3",
    "days_1",
    "same_day",
    "overdue",
    name="remindertype",
    create_type=False,
)
reminder_status_enum = postgresql.ENUM("pending", "sent", "failed", "canceled", name="reminderstatus", create_type=False)
law_review_enum = postgresql.ENUM(
    "unreviewed",
    "approved",
    "rejected",
    name="lawupdatereviewstatus",
    create_type=False,
)
finance_record_type_enum = postgresql.ENUM("income", "expense", name="financerecordtype", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    entity_type_enum.create(bind, checkfirst=True)
    tax_regime_enum.create(bind, checkfirst=True)
    event_category_enum.create(bind, checkfirst=True)
    event_status_enum.create(bind, checkfirst=True)
    reminder_type_enum.create(bind, checkfirst=True)
    reminder_status_enum.create(bind, checkfirst=True)
    law_review_enum.create(bind, checkfirst=True)
    finance_record_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Europe/Moscow"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="ru"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    op.create_table(
        "business_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", entity_type_enum, nullable=False),
        sa.Column("tax_regime", tax_regime_enum, nullable=False),
        sa.Column("has_employees", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marketplaces_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("region", sa.String(length=128), nullable=False),
        sa.Column("industry", sa.String(length=128), nullable=True),
        sa.Column("reminder_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_business_profiles_user_id"),
    )

    op.create_table(
        "calendar_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", event_category_enum, nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("applies_to_entity_types", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("applies_to_tax_regimes", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("applies_if_has_employees", sa.Boolean(), nullable=True),
        sa.Column("applies_if_marketplaces", sa.Boolean(), nullable=True),
        sa.Column("applies_to_regions", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("legal_basis", sa.Text(), nullable=True),
        sa.Column("recurrence_rule", sa.String(length=255), nullable=True),
        sa.Column("notification_offsets", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_calendar_events_slug"),
    )

    op.create_table(
        "user_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("calendar_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", event_status_enum, nullable=False, server_default="pending"),
        sa.Column("dismissed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "calendar_event_id", "due_date", name="uq_user_event_by_template_due_date"),
    )

    op.create_table(
        "reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reminder_type", reminder_type_enum, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", reminder_status_enum, nullable=False, server_default="pending"),
        sa.Column("delivery_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_event_id", "reminder_type", name="uq_reminder_per_type"),
    )

    op.create_table(
        "law_updates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("importance_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("affected_entity_types", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("affected_tax_regimes", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("affected_marketplaces", sa.Boolean(), nullable=True),
        sa.Column("action_required", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("review_status", law_review_enum, nullable=False, server_default="unreviewed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "law_update_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("law_update_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("law_updates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("law_update_id", "user_id", name="uq_law_delivery_once"),
    )

    op.create_table(
        "finance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("record_type", finance_record_type_enum, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="RUB"),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("subcategory", sa.String(length=128), nullable=True),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("parsed_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_dialogs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "admin_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("admin_logs")
    op.drop_table("ai_dialogs")
    op.drop_table("finance_records")
    op.drop_table("law_update_deliveries")
    op.drop_table("law_updates")
    op.drop_table("reminders")
    op.drop_table("user_events")
    op.drop_table("calendar_events")
    op.drop_table("business_profiles")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    finance_record_type_enum.drop(bind, checkfirst=True)
    law_review_enum.drop(bind, checkfirst=True)
    reminder_status_enum.drop(bind, checkfirst=True)
    reminder_type_enum.drop(bind, checkfirst=True)
    event_status_enum.drop(bind, checkfirst=True)
    event_category_enum.drop(bind, checkfirst=True)
    tax_regime_enum.drop(bind, checkfirst=True)
    entity_type_enum.drop(bind, checkfirst=True)
