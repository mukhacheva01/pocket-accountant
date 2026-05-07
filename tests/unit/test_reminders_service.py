"""Tests for ReminderService (create_reminders_for_event, due_reminders)."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

from shared.db.enums import EventCategory, ReminderType
from backend.services.reminders import ReminderService


def _make_service():
    repo = AsyncMock()
    repo.schedule_many = AsyncMock()
    repo.list_due = AsyncMock(return_value=[])
    return ReminderService(repo)


class TestReminderServiceCreateReminders:
    async def test_no_calendar_event(self):
        svc = _make_service()
        ue = SimpleNamespace(calendar_event=None)
        result = await svc.create_reminders_for_event(ue, {}, "UTC")
        assert result == []
        svc.reminders.schedule_many.assert_not_awaited()

    async def test_event_not_matching_preferences(self):
        svc = _make_service()
        ce = SimpleNamespace(category=EventCategory.TAX)
        ue = SimpleNamespace(
            calendar_event=ce,
            due_date=date(2026, 7, 15),
            user_id="u1",
            id="ue1",
        )
        profile_settings = {"notify_taxes": False, "notify_reporting": False, "notify_documents": False}
        result = await svc.create_reminders_for_event(ue, profile_settings, "UTC")
        assert result == []

    async def test_creates_reminders_with_defaults(self):
        svc = _make_service()
        ce = SimpleNamespace(category=EventCategory.TAX)
        ue = SimpleNamespace(
            calendar_event=ce,
            due_date=date(2026, 7, 15),
            user_id="u1",
            id="ue1",
        )
        result = await svc.create_reminders_for_event(ue, {}, "Europe/Moscow")
        assert len(result) > 0
        svc.reminders.schedule_many.assert_awaited_once()

    async def test_creates_reminders_with_custom_offsets(self):
        svc = _make_service()
        ce = SimpleNamespace(category=EventCategory.REPORT)
        ue = SimpleNamespace(
            calendar_event=ce,
            due_date=date(2026, 8, 1),
            user_id="u2",
            id="ue2",
        )
        result = await svc.create_reminders_for_event(
            ue, {"offset_days": [7, 3, 1, 0]}, "UTC",
        )
        types = {r.reminder_type for r in result}
        assert ReminderType.DAYS_7 in types
        assert ReminderType.OVERDUE in types
        svc.reminders.schedule_many.assert_awaited_once()


class TestReminderServiceDueReminders:
    async def test_due_reminders_delegates(self):
        svc = _make_service()
        svc.reminders.list_due = AsyncMock(return_value=["r1", "r2"])
        result = await svc.due_reminders(50)
        assert result == ["r1", "r2"]
        svc.reminders.list_due.assert_awaited_once()
