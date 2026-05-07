"""Tests for shared.contracts.payloads."""

from datetime import date, datetime, timezone
from decimal import Decimal

from shared.contracts.payloads import FinanceRecordPayload, LawUpdatePayload, ReminderPayload
from shared.db.enums import FinanceRecordType, ReminderType


def test_reminder_payload():
    p = ReminderPayload(
        reminder_id="r1",
        user_id="u1",
        user_event_id="ue1",
        reminder_type=ReminderType.DAYS_3,
        scheduled_at=datetime(2026, 6, 12, 9, 0, tzinfo=timezone.utc),
        due_date=date(2026, 6, 15),
        title="Налог",
        description="Уплата налога",
        category="tax",
        action_required="Оплатите",
    )
    assert p.reminder_id == "r1"
    assert p.buttons == []
    assert p.consequence_hint is None


def test_law_update_payload():
    p = LawUpdatePayload(
        law_update_id="lu1",
        source="ФНС",
        title="Новый закон",
        summary="Описание",
        published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        importance_score=8,
        source_url="https://example.com",
    )
    assert p.needs_admin_review is True
    assert p.affected_profiles == []


def test_finance_record_payload():
    p = FinanceRecordPayload(
        record_type=FinanceRecordType.INCOME,
        amount=Decimal("5000"),
        category="services",
        operation_date=date(2026, 1, 15),
        source_text="получил за услуги",
    )
    assert p.currency == "RUB"
    assert p.confidence == 0.0
    assert p.subcategory is None
