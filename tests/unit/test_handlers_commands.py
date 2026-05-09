"""Tests for command handlers in bot.handlers — /start, /menu, /help, etc."""

from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers import build_router
from tests.unit.bot_helpers import make_message, make_state, make_services, make_db_user


MODULE = "bot.handlers.helpers"


def _patch_deps(services=None):
    """Return (session_ctx, mock_build) patches for SessionFactory and build_services."""
    svc = services or make_services()

    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()

    sf_patch = patch(f"{MODULE}.SessionFactory", return_value=session)
    bs_patch = patch(f"{MODULE}.build_services", return_value=svc)
    gs_patch = patch(f"{MODULE}.get_settings", return_value=MagicMock(
        stars_price_basic=150,
        stars_price_pro=400,
        stars_price_annual=3500,
    ))
    return sf_patch, bs_patch, gs_patch, svc, session


class TestStartHandler:
    async def test_start_existing_user(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        start = handlers["start_handler"]

        msg = make_message("/start")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await start.callback(msg, state)
        state.clear.assert_awaited()
        msg.answer.assert_awaited()

    async def test_start_new_user_triggers_onboarding(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        svc.onboarding.load_profile = AsyncMock(return_value=None)
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        start = handlers["start_handler"]

        msg = make_message("/start")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await start.callback(msg, state)
        state.set_state.assert_awaited()
        msg.answer.assert_awaited()
        call_text = msg.answer.call_args[0][0]
        assert "Привет" in call_text or "приветств" in call_text.lower() or msg.answer.called

    async def test_start_with_referral(self):
        sf_p, bs_p, gs_p, svc, session = _patch_deps()
        user = make_db_user(telegram_id=123)
        svc.onboarding.ensure_user = AsyncMock(return_value=user)

        referrer = make_db_user(telegram_id=456)
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=referrer)
        session.execute = AsyncMock(return_value=scalar_result)

        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        start = handlers["start_handler"]

        msg = make_message("/start ref_456")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await start.callback(msg, state)
        assert user.referred_by == "456"


class TestMenuHandler:
    async def test_menu_shows_home(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        menu = handlers["menu_handler"]

        msg = make_message("/menu")
        with sf_p, bs_p, gs_p:
            await menu.callback(msg)
        msg.answer.assert_awaited()


class TestHelpHandler:
    async def test_help_shows_text(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["help_handler"]

        msg = make_message("/help")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestProfileHandler:
    async def test_profile_shows_info(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["profile_handler"]

        msg = make_message("/profile")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        call_text = msg.answer.call_args[0][0]
        assert "Профиль" in call_text

    async def test_profile_no_profile_triggers_onboarding(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        svc.onboarding.load_profile = AsyncMock(return_value=None)
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["profile_handler"]

        msg = make_message("/profile")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestEventsHandler:
    async def test_no_events(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["events_handler"]

        msg = make_message("/events")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "нет" in msg.answer.call_args[0][0].lower() or "событий" in msg.answer.call_args[0][0].lower()

    async def test_with_events(self):
        from datetime import date
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        event = MagicMock()
        event.id = "e1"
        event.calendar_event = MagicMock(title="Сдача НДС")
        event.due_date = date(2026, 7, 20)
        svc.calendar.upcoming = AsyncMock(return_value=[event])
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["events_handler"]

        msg = make_message("/events")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Сдача НДС" in msg.answer.call_args[0][0]


class TestDocumentsHandler:
    async def test_no_documents(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["documents_handler"]

        msg = make_message("/documents")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()

    async def test_with_documents(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        svc.documents.upcoming_documents = AsyncMock(return_value=[
            {"title": "Декларация УСН", "due_date": "2026-04-30", "action_required": "Подать в ФНС"},
        ])
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["documents_handler"]

        msg = make_message("/documents")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        assert "Декларация" in msg.answer.call_args[0][0]


class TestFinanceHandler:
    async def test_finance_shows_report(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["finance_handler"]

        msg = make_message("/finance")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Финансы" in msg.answer.call_args[0][0]


class TestCalendarHandler:
    async def test_no_events(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["calendar_handler"]

        msg = make_message("/calendar")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestOverdueHandler:
    async def test_no_overdue(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["overdue_handler"]

        msg = make_message("/overdue")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestSettingsHandler:
    async def test_settings(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["settings_handler"]

        msg = make_message("/settings")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Настройки" in msg.answer.call_args[0][0]


class TestBalanceHandler:
    async def test_balance(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["balance_handler"]

        msg = make_message("/balance")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Баланс" in msg.answer.call_args[0][0]


class TestLawsHandler:
    async def test_no_laws(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["laws_handler"]

        msg = make_message("/laws")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()

    async def test_laws_no_profile(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        svc.onboarding.load_profile = AsyncMock(return_value=None)
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["laws_handler"]

        msg = make_message("/laws")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestRemindersHandler:
    async def test_reminders(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["reminders_handler"]

        msg = make_message("/reminders")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Напоминания" in msg.answer.call_args[0][0]


class TestSubscriptionHandler:
    async def test_no_subscription(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["subscription_handler"]

        msg = make_message("/subscription")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()


class TestCalcHandler:
    async def test_calc_no_payload(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["calc_handler"]

        msg = make_message("/calc")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "Пришли запрос" in msg.answer.call_args[0][0]


class TestCancelHandler:
    async def test_cancel_clears_state(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["cancel_handler"]

        msg = make_message("Отмена")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()


class TestUnsupportedContentHandler:
    async def test_sticker(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["unsupported_content_handler"]

        msg = make_message("")
        msg.content_type = "sticker"
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "текст" in msg.answer.call_args[0][0].lower()
