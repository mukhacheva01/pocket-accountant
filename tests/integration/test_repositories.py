"""Integration tests for repositories using in-memory SQLite."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import JSON, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.db.base import Base


# Patch ARRAY columns to JSON for SQLite compatibility
def _patch_array_columns():
    from sqlalchemy.dialects.postgresql import ARRAY
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, ARRAY):
                col.type = JSON()
from shared.db.enums import (
    EntityType,
    EventCategory,
    EventStatus,
    FinanceRecordType,
    LawUpdateReviewStatus,
    ReminderStatus,
    ReminderType,
    SubscriptionPlan,
    TaxRegime,
)
from shared.db.models import (
    CalendarEvent,
    FinanceRecord,
    LawUpdate,
    LawUpdateDelivery,
    MarketplaceConnection,
    Payment,
    Reminder,
    Subscription,
    User,
    UserEvent,
)
from backend.repositories.events import CalendarEventRepository
from backend.repositories.finance import FinanceRepository
from backend.repositories.law_updates import LawUpdateRepository
from backend.repositories.marketplace_connections import MarketplaceConnectionRepository
from backend.repositories.reminders import ReminderRepository
from backend.repositories.subscriptions import SubscriptionRepository
from backend.repositories.users import BusinessProfileRepository, UserRepository


@pytest.fixture()
async def db_session():
    _patch_array_columns()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


class TestUserRepository:
    async def test_create_user(self, db_session):
        repo = UserRepository(db_session)
        user = await repo.create_or_update_user(111, "alice", "Alice", "Europe/Moscow")
        assert user.telegram_id == 111
        assert user.username == "alice"

    async def test_update_user(self, db_session):
        repo = UserRepository(db_session)
        await repo.create_or_update_user(111, "alice", "Alice", "Europe/Moscow")
        user = await repo.create_or_update_user(111, "alice_new", "Alice New", "Europe/Moscow")
        assert user.username == "alice_new"

    async def test_get_by_telegram_id(self, db_session):
        repo = UserRepository(db_session)
        await repo.create_or_update_user(222, "bob", "Bob", "UTC")
        found = await repo.get_by_telegram_id(222)
        assert found is not None
        assert found.first_name == "Bob"

    async def test_get_nonexistent(self, db_session):
        repo = UserRepository(db_session)
        found = await repo.get_by_telegram_id(999)
        assert found is None


class TestBusinessProfileRepository:
    async def test_create_profile(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")

        repo = BusinessProfileRepository(db_session)
        profile = await repo.upsert(user.id, {
            "entity_type": EntityType.INDIVIDUAL_ENTREPRENEUR,
            "tax_regime": TaxRegime.USN_INCOME,
            "has_employees": False,
            "region": "Moscow",
        })
        assert profile.entity_type == EntityType.INDIVIDUAL_ENTREPRENEUR

    async def test_update_profile(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")

        repo = BusinessProfileRepository(db_session)
        await repo.upsert(user.id, {
            "entity_type": EntityType.INDIVIDUAL_ENTREPRENEUR,
            "tax_regime": TaxRegime.USN_INCOME,
            "has_employees": False,
            "region": "Moscow",
        })
        profile = await repo.upsert(user.id, {"region": "SPb"})
        assert profile.region == "SPb"

    async def test_get_nonexistent(self, db_session):
        import uuid as uuid_mod
        repo = BusinessProfileRepository(db_session)
        result = await repo.get_by_user_id(uuid_mod.uuid4())
        assert result is None


class TestFinanceRepository:
    async def test_add_and_list(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = FinanceRepository(db_session)
        record = FinanceRecord(
            user_id=uid,
            record_type=FinanceRecordType.INCOME,
            amount=Decimal("5000"),
            category="services",
            operation_date=date(2026, 6, 1),
            source_text="test income",
        )
        await repo.add_record(record)
        records = await repo.list_records(uid)
        assert len(records) == 1

    async def test_summarize_period(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = FinanceRepository(db_session)
        await repo.add_record(FinanceRecord(
            user_id=uid, record_type=FinanceRecordType.INCOME,
            amount=Decimal("1000"), category="services",
            operation_date=date(2026, 6, 1), source_text="income",
        ))
        await repo.add_record(FinanceRecord(
            user_id=uid, record_type=FinanceRecordType.EXPENSE,
            amount=Decimal("400"), category="marketing",
            operation_date=date(2026, 6, 2), source_text="expense",
        ))
        totals = await repo.summarize_period(uid, date(2026, 6, 1), date(2026, 6, 30))
        assert totals["income"] == Decimal("1000")
        assert totals["expense"] == Decimal("400")

    async def test_top_expense_categories(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = FinanceRepository(db_session)
        await repo.add_record(FinanceRecord(
            user_id=uid, record_type=FinanceRecordType.EXPENSE,
            amount=Decimal("500"), category="marketing",
            operation_date=date(2026, 6, 1), source_text="ads",
        ))
        top = await repo.top_expense_categories(uid)
        assert len(top) == 1

    async def test_list_records_with_filters(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = FinanceRepository(db_session)
        await repo.add_record(FinanceRecord(
            user_id=uid, record_type=FinanceRecordType.INCOME,
            amount=Decimal("1000"), category="services",
            operation_date=date(2026, 6, 1), source_text="income",
        ))
        await repo.add_record(FinanceRecord(
            user_id=uid, record_type=FinanceRecordType.EXPENSE,
            amount=Decimal("200"), category="rent",
            operation_date=date(2026, 6, 5), source_text="rent",
        ))
        income_only = await repo.list_records(uid, record_type=FinanceRecordType.INCOME)
        assert len(income_only) == 1
        dated = await repo.list_records(uid, date_from=date(2026, 6, 3))
        assert len(dated) == 1


class TestSubscriptionRepository:
    async def test_upsert_create(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = SubscriptionRepository(db_session)
        sub = await repo.upsert(uid, {"plan": SubscriptionPlan.BASIC})
        assert sub.plan == SubscriptionPlan.BASIC

    async def test_upsert_update(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = SubscriptionRepository(db_session)
        await repo.upsert(uid, {"plan": SubscriptionPlan.BASIC})
        sub = await repo.upsert(uid, {"plan": SubscriptionPlan.PRO})
        assert sub.plan == SubscriptionPlan.PRO

    async def test_get_nonexistent(self, db_session):
        import uuid as uuid_mod
        repo = SubscriptionRepository(db_session)
        result = await repo.get_by_user_id(uuid_mod.uuid4())
        assert result is None

    async def test_add_payment(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = SubscriptionRepository(db_session)
        payment = Payment(user_id=uid, amount_stars=150, plan=SubscriptionPlan.BASIC, telegram_payment_id="tg_pay_1")
        result = await repo.add_payment(payment)
        assert result.telegram_payment_id == "tg_pay_1"

    async def test_payment_exists(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = SubscriptionRepository(db_session)
        assert await repo.payment_exists("tg_pay_1") is False
        assert await repo.payment_exists("") is False

        payment = Payment(user_id=uid, amount_stars=150, plan=SubscriptionPlan.BASIC, telegram_payment_id="tg_pay_1")
        await repo.add_payment(payment)
        assert await repo.payment_exists("tg_pay_1") is True


class TestLawUpdateRepository:
    async def test_list_approved(self, db_session):
        repo = LawUpdateRepository(db_session)
        update = LawUpdate(
            source="ФНС", source_url="https://fns.ru/1",
            title="Закон", summary="Summary",
            published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            importance_score=8, review_status=LawUpdateReviewStatus.APPROVED,
            is_active=True,
        )
        db_session.add(update)
        await db_session.flush()
        results = await repo.list_approved(5)
        assert len(results) == 1

    async def test_list_pending_review(self, db_session):
        repo = LawUpdateRepository(db_session)
        update = LawUpdate(
            source="ФНС", source_url="https://fns.ru/1",
            title="Pending", summary="Summary",
            published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            importance_score=3, review_status=LawUpdateReviewStatus.UNREVIEWED,
            is_active=True,
        )
        db_session.add(update)
        await db_session.flush()
        results = await repo.list_pending_review()
        assert len(results) == 1

    async def test_was_delivered_and_mark(self, db_session):
        repo = LawUpdateRepository(db_session)
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        update = LawUpdate(
            source="ФНС", source_url="https://fns.ru/1",
            title="Test", summary="Sum",
            published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            importance_score=5, review_status=LawUpdateReviewStatus.APPROVED,
            is_active=True,
        )
        db_session.add(update)
        await db_session.flush()

        assert await repo.was_delivered(update.id, uid) is False
        await repo.mark_delivered(update.id, uid, datetime.now(timezone.utc), "sent")
        assert await repo.was_delivered(update.id, uid) is True

        # Mark again to test update path
        await repo.mark_delivered(update.id, uid, datetime.now(timezone.utc), "resent")


class TestMarketplaceConnectionRepository:
    async def test_upsert_create(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = MarketplaceConnectionRepository(db_session)
        conn = await repo.upsert(uid, {"seller_id": "S123", "api_key_secret": "key", "api_key_masked": "k***y", "status": "pending"})
        assert conn.seller_id == "S123"

    async def test_upsert_update(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = MarketplaceConnectionRepository(db_session)
        await repo.upsert(uid, {"seller_id": "S123", "api_key_secret": "key", "api_key_masked": "k***y", "status": "pending"})
        conn = await repo.upsert(uid, {"status": "active"})
        assert conn.status == "active"

    async def test_get_nonexistent(self, db_session):
        import uuid as uuid_mod
        repo = MarketplaceConnectionRepository(db_session)
        result = await repo.get_by_user_id(uuid_mod.uuid4())
        assert result is None


class TestCalendarEventRepository:
    async def test_list_active_templates(self, db_session):
        repo = CalendarEventRepository(db_session)
        event = CalendarEvent(
            slug="usn-tax-2026",
            title="Налог УСН", description="Уплата",
            category=EventCategory.TAX, priority=1,
            legal_basis="НК", active=True,
            due_date=date(2026, 7, 15),
            applies_to_entity_types=["ip"],
        )
        db_session.add(event)
        await db_session.flush()
        templates = await repo.list_active_templates()
        assert len(templates) >= 1

    async def test_upsert_user_event(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        event = CalendarEvent(
            slug="decl-2026",
            title="Декларация", description="Сдача",
            category=EventCategory.DECLARATION, priority=1,
            legal_basis="НК", active=True,
            due_date=date(2026, 7, 15),
        )
        db_session.add(event)
        await db_session.flush()

        repo = CalendarEventRepository(db_session)
        ue = await repo.upsert_user_event(uid, event, date(2026, 7, 15))
        assert ue.status == EventStatus.PENDING

        # Upsert again — should update existing
        ue2 = await repo.upsert_user_event(uid, event, date(2026, 7, 15))
        assert ue2.id == ue.id

    async def test_list_upcoming_for_user(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = CalendarEventRepository(db_session)
        result = await repo.list_upcoming_for_user(uid, date(2026, 12, 31))
        assert isinstance(result, list)

    async def test_list_upcoming_include_overdue(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        repo = CalendarEventRepository(db_session)
        result = await repo.list_upcoming_for_user(uid, date(2026, 12, 31), include_overdue=True)
        assert isinstance(result, list)


class TestReminderRepository:
    async def test_schedule_many_and_list_due(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        event = CalendarEvent(
            slug="tax-reminder-1",
            title="Налог", description="Уплата",
            category=EventCategory.TAX, priority=1,
            legal_basis="НК", active=True,
            due_date=date(2026, 7, 15),
        )
        db_session.add(event)
        await db_session.flush()

        cal_repo = CalendarEventRepository(db_session)
        ue = await cal_repo.upsert_user_event(uid, event, date(2026, 7, 15))

        repo = ReminderRepository(db_session)
        now = datetime(2026, 7, 12, 9, 0, tzinfo=timezone.utc)
        reminder = Reminder(
            user_id=uid, user_event_id=ue.id,
            reminder_type=ReminderType.DAYS_3,
            scheduled_at=now,
            status=ReminderStatus.PENDING,
        )
        await repo.schedule_many([reminder])
        due = await repo.list_due(datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc), 10)
        assert len(due) == 1

    async def test_schedule_many_updates_existing(self, db_session):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_or_update_user(111, "alice", "Alice", "UTC")
        uid = user.id

        event = CalendarEvent(
            slug="tax-reminder-2",
            title="Налог", description="Уплата",
            category=EventCategory.TAX, priority=1,
            legal_basis="НК", active=True,
            due_date=date(2026, 7, 15),
        )
        db_session.add(event)
        await db_session.flush()

        cal_repo = CalendarEventRepository(db_session)
        ue = await cal_repo.upsert_user_event(uid, event, date(2026, 7, 15))

        repo = ReminderRepository(db_session)
        now1 = datetime(2026, 7, 12, 9, 0, tzinfo=timezone.utc)
        r1 = Reminder(
            user_id=uid, user_event_id=ue.id,
            reminder_type=ReminderType.DAYS_3,
            scheduled_at=now1,
            status=ReminderStatus.PENDING,
        )
        await repo.schedule_many([r1])

        # Schedule again — should update
        now2 = datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)
        r2 = Reminder(
            user_id=uid, user_event_id=ue.id,
            reminder_type=ReminderType.DAYS_3,
            scheduled_at=now2,
            status=ReminderStatus.PENDING,
        )
        await repo.schedule_many([r2])
