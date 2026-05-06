"""Tests for worker.tasks — background job functions."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


from shared.db.enums import EntityType, EventCategory, ReminderStatus, ReminderType, TaxRegime


class TestSyncUserEvents:
    @patch("worker.tasks.SessionFactory")
    @patch("worker.tasks.build_services")
    async def test_processes_users(self, mock_build, mock_sf):
        from worker.tasks import sync_user_events

        session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_sf.return_value.__aexit__ = AsyncMock()

        user = MagicMock()
        user.id = "u1"
        user.timezone = "Europe/Moscow"
        result = MagicMock()
        result.scalars.return_value.all.return_value = [user]
        session.execute = AsyncMock(return_value=result)
        session.commit = AsyncMock()

        services = MagicMock()
        profile = MagicMock()
        profile.entity_type = EntityType.INDIVIDUAL_ENTREPRENEUR
        profile.tax_regime = TaxRegime.USN_INCOME
        profile.has_employees = False
        profile.marketplaces_enabled = False
        profile.region = "Moscow"
        profile.industry = None
        profile.reminder_settings = {"offset_days": [3, 1]}
        services.onboarding.load_profile = AsyncMock(return_value=profile)
        services.calendar.sync_user_events = AsyncMock()
        services.calendar.upcoming = AsyncMock(return_value=[])
        mock_build.return_value = services

        await sync_user_events()
        services.onboarding.load_profile.assert_awaited_once()
        services.calendar.sync_user_events.assert_awaited_once()
        session.commit.assert_awaited_once()

    @patch("worker.tasks.SessionFactory")
    @patch("worker.tasks.build_services")
    async def test_skips_user_without_profile(self, mock_build, mock_sf):
        from worker.tasks import sync_user_events

        session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_sf.return_value.__aexit__ = AsyncMock()

        user = MagicMock()
        user.id = "u1"
        result = MagicMock()
        result.scalars.return_value.all.return_value = [user]
        session.execute = AsyncMock(return_value=result)
        session.commit = AsyncMock()

        services = MagicMock()
        services.onboarding.load_profile = AsyncMock(return_value=None)
        mock_build.return_value = services

        await sync_user_events()
        services.calendar.sync_user_events.assert_not_called()


class TestSendDueReminders:
    @patch("worker.tasks.SessionFactory")
    @patch("worker.tasks.build_services")
    async def test_sends_reminders(self, mock_build, mock_sf):
        from worker.tasks import send_due_reminders

        session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_sf.return_value.__aexit__ = AsyncMock()
        session.commit = AsyncMock()

        user_event = MagicMock()
        user_event.user.telegram_id = 123
        calendar_event = MagicMock()
        calendar_event.title = "Налог"
        calendar_event.description = "Уплата авансового платежа"
        calendar_event.category = EventCategory.TAX
        calendar_event.legal_basis = "НК"
        user_event.calendar_event = calendar_event
        user_event.due_date = date(2026, 7, 15)
        user_event.id = "ue1"

        reminder = MagicMock()
        reminder.user_event = user_event
        reminder.user_id = "u1"
        reminder.id = "r1"
        reminder.reminder_type = ReminderType.DAYS_3
        reminder.scheduled_at = datetime(2026, 7, 12, 9, 0, tzinfo=timezone.utc)
        reminder.delivery_payload = {"action_required": "Уплатите налог"}

        services = MagicMock()
        services.reminders.due_reminders = AsyncMock(return_value=[reminder])
        mock_build.return_value = services

        bot = AsyncMock()
        bot.send_message = AsyncMock()

        await send_due_reminders(bot, 10)
        bot.send_message.assert_awaited_once()
        assert reminder.status == ReminderStatus.SENT

    @patch("worker.tasks.SessionFactory")
    @patch("worker.tasks.build_services")
    async def test_handles_blocked_user(self, mock_build, mock_sf):
        from aiogram.exceptions import TelegramForbiddenError
        from worker.tasks import send_due_reminders

        session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_sf.return_value.__aexit__ = AsyncMock()
        session.commit = AsyncMock()

        user_event = MagicMock()
        user_event.user.telegram_id = 123
        user_event.id = "ue1"
        user_event.calendar_event = MagicMock()
        user_event.calendar_event.title = "T"
        user_event.calendar_event.description = "Desc"
        user_event.calendar_event.category = EventCategory.TAX
        user_event.calendar_event.legal_basis = "НК"
        user_event.due_date = date(2026, 7, 15)

        reminder = MagicMock()
        reminder.user_event = user_event
        reminder.user_id = "u1"
        reminder.id = "r1"
        reminder.reminder_type = ReminderType.DAYS_3
        reminder.scheduled_at = datetime(2026, 7, 12, 9, 0, tzinfo=timezone.utc)
        reminder.delivery_payload = {"action_required": "Уплатите"}

        services = MagicMock()
        services.reminders.due_reminders = AsyncMock(return_value=[reminder])
        mock_build.return_value = services

        user_for_deactivate = MagicMock()
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user_for_deactivate
        session.execute = AsyncMock(return_value=user_result)

        bot = AsyncMock()
        bot.send_message = AsyncMock(side_effect=TelegramForbiddenError(method=MagicMock(), message="Forbidden"))

        await send_due_reminders(bot, 10)
        assert reminder.status == ReminderStatus.FAILED
        assert user_for_deactivate.is_active is False


class TestDeliverLawUpdates:
    @patch("worker.tasks.SessionFactory")
    @patch("worker.tasks.build_services")
    async def test_delivers_updates(self, mock_build, mock_sf):
        from worker.tasks import deliver_law_updates

        session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_sf.return_value.__aexit__ = AsyncMock()
        session.commit = AsyncMock()

        result = MagicMock()
        result.fetchall.return_value = [("u1",)]
        session.execute = AsyncMock(return_value=result)

        profile = MagicMock()
        profile.entity_type = EntityType.INDIVIDUAL_ENTREPRENEUR
        profile.tax_regime = TaxRegime.USN_INCOME
        profile.has_employees = False
        profile.marketplaces_enabled = False
        profile.region = "Moscow"
        profile.industry = None
        profile.reminder_settings = {}
        profile.user = MagicMock()
        profile.user.telegram_id = 123

        update = MagicMock()
        update.id = "lu1"
        update.title = "Новый закон"
        update.source = "ФНС"
        update.action_required = "Проверь"

        services = MagicMock()
        services.onboarding.load_profile = AsyncMock(return_value=profile)
        services.laws.relevant_updates = AsyncMock(return_value=[update])
        services.laws.was_delivered = AsyncMock(return_value=False)
        services.laws.mark_delivered = AsyncMock()
        mock_build.return_value = services

        bot = AsyncMock()
        bot.send_message = AsyncMock()

        await deliver_law_updates(bot, 3)
        bot.send_message.assert_awaited_once()
        services.laws.mark_delivered.assert_awaited_once()

    @patch("worker.tasks.SessionFactory")
    @patch("worker.tasks.build_services")
    async def test_skips_no_profile(self, mock_build, mock_sf):
        from worker.tasks import deliver_law_updates

        session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_sf.return_value.__aexit__ = AsyncMock()
        session.commit = AsyncMock()

        result = MagicMock()
        result.fetchall.return_value = [("u1",)]
        session.execute = AsyncMock(return_value=result)

        services = MagicMock()
        services.onboarding.load_profile = AsyncMock(return_value=None)
        mock_build.return_value = services

        bot = AsyncMock()
        await deliver_law_updates(bot, 3)
        bot.send_message.assert_not_called()
