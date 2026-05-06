"""Tests for backend.services.reminders."""

from datetime import date, datetime, timezone

from shared.db.enums import EventCategory, ReminderType
from backend.services.reminders import ReminderPlanner, REMINDER_TYPE_TO_OFFSET


class TestReminderPlanner:
    def test_build_schedule_with_offsets(self):
        due = date(2026, 6, 15)
        plans = ReminderPlanner.build_schedule(due, [3, 1], "Europe/Moscow")
        types = {p.reminder_type for p in plans}
        assert ReminderType.DAYS_3 in types
        assert ReminderType.DAYS_1 in types
        assert ReminderType.OVERDUE in types
        assert ReminderType.DAYS_7 not in types

    def test_build_schedule_all_offsets(self):
        due = date(2026, 6, 15)
        plans = ReminderPlanner.build_schedule(due, [7, 3, 1, 0], "UTC")
        types = {p.reminder_type for p in plans}
        assert ReminderType.DAYS_7 in types
        assert ReminderType.DAYS_3 in types
        assert ReminderType.DAYS_1 in types
        assert ReminderType.SAME_DAY in types
        assert ReminderType.OVERDUE in types

    def test_overdue_always_included(self):
        due = date(2026, 6, 15)
        plans = ReminderPlanner.build_schedule(due, [], "UTC")
        assert len(plans) == 1
        assert plans[0].reminder_type == ReminderType.OVERDUE

    def test_schedule_times_are_utc(self):
        due = date(2026, 6, 15)
        plans = ReminderPlanner.build_schedule(due, [1], "UTC")
        for plan in plans:
            assert plan.scheduled_at.tzinfo == timezone.utc

    def test_action_required_text(self):
        due = date(2026, 6, 15)
        plans = ReminderPlanner.build_schedule(due, [1], "UTC")
        for plan in plans:
            assert plan.action_required

    def test_invalid_timezone_falls_back_to_utc(self):
        due = date(2026, 6, 15)
        plans = ReminderPlanner.build_schedule(due, [1], "Invalid/TZ")
        assert len(plans) == 2
        for plan in plans:
            assert plan.scheduled_at.tzinfo == timezone.utc


class TestReminderTypeToOffset:
    def test_mapping(self):
        assert REMINDER_TYPE_TO_OFFSET[ReminderType.DAYS_7] == 7
        assert REMINDER_TYPE_TO_OFFSET[ReminderType.DAYS_3] == 3
        assert REMINDER_TYPE_TO_OFFSET[ReminderType.DAYS_1] == 1
        assert REMINDER_TYPE_TO_OFFSET[ReminderType.SAME_DAY] == 0
