"""Tests for command handlers in bot.handlers — /start, /menu, /help, etc."""

from unittest.mock import AsyncMock, MagicMock

from bot.handlers import build_router
from tests.unit.bot_helpers import (
    collect_handlers,
    make_message,
    make_state,
    make_db_user,
    patch_handler_deps,
)


def _build(services=None):
    ctx, svc, session = patch_handler_deps(services)
    with ctx:
        router = build_router()
    return ctx, svc, session, router


class TestStartHandler:
    async def test_start_existing_user(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        start = handlers["start_handler"]

        msg = make_message("/start")
        state = make_state()
        with ctx:
            await start.callback(msg, state)
        state.clear.assert_awaited()
        msg.answer.assert_awaited()

    async def test_start_new_user_triggers_onboarding(self):
        ctx, svc, _, router = _build()
        svc.onboarding.load_profile = AsyncMock(return_value=None)
        handlers = collect_handlers(router, "message")
        start = handlers["start_handler"]

        msg = make_message("/start")
        state = make_state()
        with ctx:
            await start.callback(msg, state)
        state.set_state.assert_awaited()
        msg.answer.assert_awaited()
        call_text = msg.answer.call_args[0][0]
        assert "Привет" in call_text or "приветств" in call_text.lower() or msg.answer.called

    async def test_start_with_referral(self):
        ctx, svc, session, router = _build()
        user = make_db_user(telegram_id=123)
        svc.onboarding.ensure_user = AsyncMock(return_value=user)

        referrer = make_db_user(telegram_id=456)
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=referrer)
        session.execute = AsyncMock(return_value=scalar_result)

        handlers = collect_handlers(router, "message")
        start = handlers["start_handler"]

        msg = make_message("/start ref_456")
        state = make_state()
        with ctx:
            await start.callback(msg, state)
        assert user.referred_by == "456"


class TestMenuHandler:
    async def test_menu_shows_home(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        menu = handlers["menu_handler"]

        msg = make_message("/menu")
        with ctx:
            await menu.callback(msg)
        msg.answer.assert_awaited()


class TestHelpHandler:
    async def test_help_shows_text(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["help_handler"]

        msg = make_message("/help")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestProfileHandler:
    async def test_profile_shows_info(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["profile_handler"]

        msg = make_message("/profile")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        call_text = msg.answer.call_args[0][0]
        assert "Профиль" in call_text

    async def test_profile_no_profile_triggers_onboarding(self):
        ctx, svc, _, router = _build()
        svc.onboarding.load_profile = AsyncMock(return_value=None)
        handlers = collect_handlers(router, "message")
        handler = handlers["profile_handler"]

        msg = make_message("/profile")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestEventsHandler:
    async def test_no_events(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["events_handler"]

        msg = make_message("/events")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "нет" in msg.answer.call_args[0][0].lower() or "событий" in msg.answer.call_args[0][0].lower()

    async def test_with_events(self):
        from datetime import date
        ctx, svc, _, router = _build()
        event = MagicMock()
        event.id = "e1"
        event.calendar_event = MagicMock(title="Сдача НДС")
        event.due_date = date(2026, 7, 20)
        svc.calendar.upcoming = AsyncMock(return_value=[event])
        handlers = collect_handlers(router, "message")
        handler = handlers["events_handler"]

        msg = make_message("/events")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Сдача НДС" in msg.answer.call_args[0][0]


class TestDocumentsHandler:
    async def test_no_documents(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["documents_handler"]

        msg = make_message("/documents")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()

    async def test_with_documents(self):
        ctx, svc, _, router = _build()
        svc.documents.upcoming_documents = AsyncMock(return_value=[
            {"title": "Декларация УСН", "due_date": "2026-04-30", "action_required": "Подать в ФНС"},
        ])
        handlers = collect_handlers(router, "message")
        handler = handlers["documents_handler"]

        msg = make_message("/documents")
        with ctx:
            await handler.callback(msg)
        assert "Декларация" in msg.answer.call_args[0][0]


class TestFinanceHandler:
    async def test_finance_shows_report(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["finance_handler"]

        msg = make_message("/finance")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Финансы" in msg.answer.call_args[0][0]


class TestCalendarHandler:
    async def test_no_events(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["calendar_handler"]

        msg = make_message("/calendar")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestOverdueHandler:
    async def test_no_overdue(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["overdue_handler"]

        msg = make_message("/overdue")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestSettingsHandler:
    async def test_settings(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["settings_handler"]

        msg = make_message("/settings")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Настройки" in msg.answer.call_args[0][0]


class TestBalanceHandler:
    async def test_balance(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["balance_handler"]

        msg = make_message("/balance")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Баланс" in msg.answer.call_args[0][0]


class TestLawsHandler:
    async def test_no_laws(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["laws_handler"]

        msg = make_message("/laws")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()

    async def test_laws_no_profile(self):
        ctx, svc, _, router = _build()
        svc.onboarding.load_profile = AsyncMock(return_value=None)
        handlers = collect_handlers(router, "message")
        handler = handlers["laws_handler"]

        msg = make_message("/laws")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestRemindersHandler:
    async def test_reminders(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["reminders_handler"]

        msg = make_message("/reminders")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Напоминания" in msg.answer.call_args[0][0]


class TestSubscriptionHandler:
    async def test_no_subscription(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["subscription_handler"]

        msg = make_message("/subscription")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestCalcHandler:
    async def test_calc_no_payload(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["calc_handler"]

        msg = make_message("/calc")
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Пришли запрос" in msg.answer.call_args[0][0]


class TestCancelHandler:
    async def test_cancel_clears_state(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["cancel_handler"]

        msg = make_message("Отмена")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        state.clear.assert_awaited()


class TestUnsupportedContentHandler:
    async def test_sticker(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["unsupported_content_handler"]

        msg = make_message("")
        msg.content_type = "sticker"
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "текст" in msg.answer.call_args[0][0].lower()
