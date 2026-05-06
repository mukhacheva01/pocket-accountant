"""Tests for callback query handlers in bot.handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

from bot.callbacks import EventActionCallback, NavigationCallback, PageCallback, SubscriptionCallback
from bot.handlers import build_router
from tests.unit.bot_helpers import (
    make_callback_query,
    make_services,
    make_state,
)


MODULE = "bot.handlers"


def _patch_deps(services=None):
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
        stars_price_basic=150, stars_price_pro=400, stars_price_annual=3500,
    ))
    return sf_patch, bs_patch, gs_patch, svc, session


class TestNavigationCallback:
    async def test_home(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="home")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_profile(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="profile")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_events(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="events")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_finance(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="finance")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_help(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="help")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_settings(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="settings")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_subscription(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="subscription")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_calendar(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="calendar")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_overdue(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="overdue")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_documents(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="documents")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_laws(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="laws")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_reminders(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="reminders")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_balance(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="balance")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_income_list(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="income_list")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_expense_list(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="expense_list")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_income_prompt(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="income_prompt")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_expense_prompt(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="expense_prompt")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_referral(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        scalar_result = MagicMock()
        scalar_result.scalar.return_value = 0
        with sf_p as sf_mock, bs_p, gs_p:
            session = sf_mock.return_value
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock(return_value=False)
            session.execute = AsyncMock(return_value=scalar_result)
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        q.message.bot.me = AsyncMock(return_value=MagicMock(username="pocket121_accountant_bot"))
        cb_data = NavigationCallback(target="referral")
        state = make_state()
        with sf_p as sf_mock, bs_p, gs_p:
            session = sf_mock.return_value
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock(return_value=False)
            session.execute = AsyncMock(return_value=scalar_result)
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_ai_exit(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_exit")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        state.clear.assert_awaited()
        q.answer.assert_awaited()

    async def test_ai_clear_history(self):
        sf_p, bs_p, gs_p, svc, session = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_clear_history")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_restart_onboarding(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="restart_onboarding")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        state.clear.assert_awaited()
        q.answer.assert_awaited()

    async def test_cancel_subscription(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="cancel_subscription")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        svc.subscription.cancel.assert_awaited()
        q.answer.assert_awaited()

    async def test_unknown_target(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="nonexistent_page")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_no_message(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        q.message = None
        cb_data = NavigationCallback(target="home")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_ai_topic_shortcut(self):
        sf_p, bs_p, gs_p, svc, session = _patch_deps()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_topic_calc")
        state = make_state()
        with sf_p, bs_p, gs_p, patch(f"{MODULE}.allow_ai_request", AsyncMock(return_value=True)):
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()


class TestSubscriptionCallback:
    async def test_buy_basic(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message.answer_invoice = AsyncMock()
        cb_data = SubscriptionCallback(action="buy", plan="basic")
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data)
        q.message.answer_invoice.assert_awaited()
        q.answer.assert_awaited()

    async def test_buy_pro(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message.answer_invoice = AsyncMock()
        cb_data = SubscriptionCallback(action="buy", plan="pro")
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data)
        q.message.answer_invoice.assert_awaited()

    async def test_buy_annual(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message.answer_invoice = AsyncMock()
        cb_data = SubscriptionCallback(action="buy", plan="annual")
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data)
        q.message.answer_invoice.assert_awaited()

    async def test_buy_unknown_plan(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        cb_data = SubscriptionCallback(action="buy", plan="unknown")
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited_with("Неизвестный тариф", show_alert=True)

    async def test_no_message(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message = None
        cb_data = SubscriptionCallback(action="buy", plan="basic")
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited()


class TestEventActionCallback:
    async def test_snooze(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["event_action_handler"]

        q = make_callback_query()
        cb_data = EventActionCallback(action="snooze", event_id="e1")
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data)
        svc.calendar.calendar_repo.snooze.assert_awaited()
        q.answer.assert_awaited()

    async def test_complete(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["event_action_handler"]

        q = make_callback_query()
        cb_data = EventActionCallback(action="complete", event_id="e1")
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data)
        svc.calendar.calendar_repo.mark_completed.assert_awaited()
        q.answer.assert_awaited()

    async def test_no_message(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["event_action_handler"]

        q = make_callback_query()
        q.message = None
        cb_data = EventActionCallback(action="snooze", event_id="e1")
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited()


class TestPageCallback:
    async def test_page(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["page_handler"]

        q = make_callback_query()
        cb_data = PageCallback(screen="events", page=2)
        with sf_p, bs_p, gs_p:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited()
