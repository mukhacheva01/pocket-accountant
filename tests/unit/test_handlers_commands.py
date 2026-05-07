"""Tests for command handlers in bot.handlers — /start, /menu, /help, etc."""

from unittest.mock import AsyncMock

from bot.handlers import build_router
from tests.unit.bot_helpers import (
    make_message,
    make_mock_client,
    make_state,
    patch_handler_deps,
)


class TestStartHandler:
    async def test_start_existing_user(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        start = handlers["start_handler"]

        msg = make_message("/start")
        state = make_state()
        with cl_p, gs_p:
            await start.callback(msg, state)
        state.clear.assert_awaited()
        msg.answer.assert_awaited()

    async def test_start_new_user_triggers_onboarding(self):
        mc = make_mock_client()
        mc.get_profile = AsyncMock(return_value={"profile": None})
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        start = handlers["start_handler"]

        msg = make_message("/start")
        state = make_state()
        with cl_p, gs_p:
            await start.callback(msg, state)
        state.set_state.assert_awaited()
        msg.answer.assert_awaited()
        call_text = msg.answer.call_args[0][0]
        assert "Привет" in call_text or "приветств" in call_text.lower() or msg.answer.called

    async def test_start_with_referral(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        start = handlers["start_handler"]

        msg = make_message("/start ref_456")
        state = make_state()
        with cl_p, gs_p:
            await start.callback(msg, state)
        mc.set_referral.assert_awaited()


class TestMenuHandler:
    async def test_menu_shows_home(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        menu = handlers["menu_handler"]

        msg = make_message("/menu")
        with cl_p, gs_p:
            await menu.callback(msg)
        msg.answer.assert_awaited()


class TestHelpHandler:
    async def test_help_shows_text(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["help_handler"]

        msg = make_message("/help")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestProfileHandler:
    async def test_profile_shows_info(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["profile_handler"]

        msg = make_message("/profile")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        call_text = msg.answer.call_args[0][0]
        assert "Профиль" in call_text

    async def test_profile_no_profile_triggers_onboarding(self):
        mc = make_mock_client()
        mc.get_profile = AsyncMock(return_value={"profile": None})
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["profile_handler"]

        msg = make_message("/profile")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestEventsHandler:
    async def test_no_events(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["events_handler"]

        msg = make_message("/events")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "нет" in msg.answer.call_args[0][0].lower() or "событий" in msg.answer.call_args[0][0].lower()

    async def test_with_events(self):
        mc = make_mock_client()
        mc.upcoming_events = AsyncMock(return_value={"events": [
            {"id": "e1", "title": "Сдача НДС", "due_date": "2026-07-20"},
        ]})
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["events_handler"]

        msg = make_message("/events")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Сдача НДС" in msg.answer.call_args[0][0]


class TestDocumentsHandler:
    async def test_no_documents(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["documents_handler"]

        msg = make_message("/documents")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()

    async def test_with_documents(self):
        mc = make_mock_client()
        mc.upcoming_documents = AsyncMock(return_value={"documents": [
            {"title": "Декларация УСН", "due_date": "2026-04-30", "action_required": "Подать в ФНС"},
        ]})
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["documents_handler"]

        msg = make_message("/documents")
        with cl_p, gs_p:
            await handler.callback(msg)
        assert "Декларация" in msg.answer.call_args[0][0]


class TestFinanceHandler:
    async def test_finance_shows_report(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["finance_handler"]

        msg = make_message("/finance")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Финансы" in msg.answer.call_args[0][0]


class TestCalendarHandler:
    async def test_no_events(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["calendar_handler"]

        msg = make_message("/calendar")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestOverdueHandler:
    async def test_no_overdue(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["overdue_handler"]

        msg = make_message("/overdue")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestSettingsHandler:
    async def test_settings(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["settings_handler"]

        msg = make_message("/settings")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Настройки" in msg.answer.call_args[0][0]


class TestBalanceHandler:
    async def test_balance(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["balance_handler"]

        msg = make_message("/balance")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Баланс" in msg.answer.call_args[0][0]


class TestLawsHandler:
    async def test_no_laws(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["laws_handler"]

        msg = make_message("/laws")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()

    async def test_laws_no_profile(self):
        mc = make_mock_client()
        mc.get_profile = AsyncMock(return_value={"profile": None})
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["laws_handler"]

        msg = make_message("/laws")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestRemindersHandler:
    async def test_reminders(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["reminders_handler"]

        msg = make_message("/reminders")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Напоминания" in msg.answer.call_args[0][0]


class TestSubscriptionHandler:
    async def test_no_subscription(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["subscription_handler"]

        msg = make_message("/subscription")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestCalcHandler:
    async def test_calc_no_payload(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["calc_handler"]

        msg = make_message("/calc")
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Пришли запрос" in msg.answer.call_args[0][0]


class TestCancelHandler:
    async def test_cancel_clears_state(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["cancel_handler"]

        msg = make_message("Отмена")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()


class TestUnsupportedContentHandler:
    async def test_sticker(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["unsupported_content_handler"]

        msg = make_message("")
        msg.content_type = "sticker"
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "текст" in msg.answer.call_args[0][0].lower()
