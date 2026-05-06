"""Tests for backend.services.notifications."""

from datetime import date, datetime, timezone
from types import SimpleNamespace

from shared.db.enums import EventCategory, ReminderType
from backend.services.notifications import NotificationComposer


def _reminder(
    rid="r1",
    uid="u1",
    ueid="ue1",
    reminder_type=ReminderType.DAYS_3,
    scheduled_at=None,
    delivery_payload=None,
):
    return SimpleNamespace(
        id=rid,
        user_id=uid,
        user_event_id=ueid,
        reminder_type=reminder_type,
        scheduled_at=scheduled_at or datetime(2026, 6, 12, 9, 0, tzinfo=timezone.utc),
        delivery_payload=delivery_payload or {},
    )


def _user_event(ueid="ue1", uid="u1", due=None):
    return SimpleNamespace(id=ueid, user_id=uid, due_date=due or date(2026, 6, 15))


def _calendar_event(category=EventCategory.TAX, title="Налог", description="Уплата"):
    return SimpleNamespace(
        category=category,
        title=title,
        description=description,
        legal_basis="НК РФ",
        priority=1,
    )


class TestNotificationComposer:
    def test_builds_reminder_payload(self):
        reminder = _reminder()
        ue = _user_event()
        ce = _calendar_event()
        payload = NotificationComposer.build_reminder_payload(reminder, ue, ce)
        assert payload.reminder_id == "r1"
        assert payload.user_id == "u1"
        assert payload.title == "Налог"
        assert payload.category == "tax"
        assert payload.legal_basis == "НК РФ"
        assert "mark_done" in payload.buttons

    def test_consequence_hint_from_payload(self):
        reminder = _reminder(delivery_payload={"consequence_hint": "custom hint", "action_required": "do it"})
        ue = _user_event()
        ce = _calendar_event()
        payload = NotificationComposer.build_reminder_payload(reminder, ue, ce)
        assert payload.consequence_hint == "custom hint"
        assert payload.action_required == "do it"

    def test_consequence_hint_fallback(self):
        reminder = _reminder(delivery_payload={})
        ue = _user_event()
        ce = _calendar_event(category=EventCategory.DECLARATION)
        payload = NotificationComposer.build_reminder_payload(reminder, ue, ce)
        assert "штраф" in payload.consequence_hint.lower()

    def test_action_required_fallback(self):
        reminder = _reminder(delivery_payload={})
        ue = _user_event()
        ce = _calendar_event()
        payload = NotificationComposer.build_reminder_payload(reminder, ue, ce)
        assert payload.action_required == "Проверьте обязательство."
