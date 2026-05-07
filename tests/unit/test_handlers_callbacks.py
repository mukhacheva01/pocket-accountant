"""Tests for callback query handlers in bot.handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

from bot.callbacks import EventActionCallback, NavigationCallback, PageCallback, SubscriptionCallback
from bot.handlers import build_router
from tests.unit.bot_helpers import (
    collect_handlers,
    make_callback_query,
    make_state,
    patch_handler_deps,
)


def _build(services=None):
    ctx, svc, session = patch_handler_deps(services)
    with ctx:
        router = build_router()
    return ctx, svc, session, router


class TestNavigationCallback:
    async def test_home(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="home")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_profile(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="profile")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_events(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="events")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_finance(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="finance")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_help(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="help")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_settings(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="settings")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_subscription(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="subscription")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_calendar(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="calendar")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_overdue(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="overdue")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_documents(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="documents")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_laws(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="laws")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_reminders(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="reminders")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_balance(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="balance")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_income_list(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="income_list")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_expense_list(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="expense_list")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_income_prompt(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="income_prompt")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_expense_prompt(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="expense_prompt")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_referral(self):
        ctx, svc, session, router = _build()
        scalar_result = MagicMock()
        scalar_result.scalar.return_value = 0
        session.execute = AsyncMock(return_value=scalar_result)
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        q.message.bot.me = AsyncMock(return_value=MagicMock(username="pocket121_accountant_bot"))
        cb_data = NavigationCallback(target="referral")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_ai_exit(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_exit")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        state.clear.assert_awaited()
        q.answer.assert_awaited()

    async def test_ai_clear_history(self):
        ctx, svc, session, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_clear_history")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_restart_onboarding(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="restart_onboarding")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        state.clear.assert_awaited()
        q.answer.assert_awaited()

    async def test_cancel_subscription(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="cancel_subscription")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        svc.subscription.cancel.assert_awaited()
        q.answer.assert_awaited()

    async def test_unknown_target(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="nonexistent_page")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_no_message(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        q.message = None
        cb_data = NavigationCallback(target="home")
        state = make_state()
        with ctx:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_ai_topic_shortcut(self):
        ctx, svc, session, router = _build()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        handlers = collect_handlers(router, "callback_query")
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_topic_calc")
        state = make_state()
        with ctx, patch("backend.services.rate_limit.allow_ai_request", AsyncMock(return_value=True)), patch("bot.handlers.navigation.allow_ai_request", AsyncMock(return_value=True)):
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()


class TestSubscriptionCallback:
    async def test_buy_basic(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message.answer_invoice = AsyncMock()
        cb_data = SubscriptionCallback(action="buy", plan="basic")
        with ctx:
            await handler.callback(q, cb_data)
        q.message.answer_invoice.assert_awaited()
        q.answer.assert_awaited()

    async def test_buy_pro(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message.answer_invoice = AsyncMock()
        cb_data = SubscriptionCallback(action="buy", plan="pro")
        with ctx:
            await handler.callback(q, cb_data)
        q.message.answer_invoice.assert_awaited()

    async def test_buy_annual(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message.answer_invoice = AsyncMock()
        cb_data = SubscriptionCallback(action="buy", plan="annual")
        with ctx:
            await handler.callback(q, cb_data)
        q.message.answer_invoice.assert_awaited()

    async def test_buy_unknown_plan(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        cb_data = SubscriptionCallback(action="buy", plan="unknown")
        with ctx:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited_with("Неизвестный тариф", show_alert=True)

    async def test_no_message(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message = None
        cb_data = SubscriptionCallback(action="buy", plan="basic")
        with ctx:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited()


class TestEventActionCallback:
    async def test_snooze(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["event_action_handler"]

        q = make_callback_query()
        cb_data = EventActionCallback(action="snooze", event_id="e1")
        with ctx:
            await handler.callback(q, cb_data)
        svc.calendar.calendar_repo.snooze.assert_awaited()
        q.answer.assert_awaited()

    async def test_complete(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["event_action_handler"]

        q = make_callback_query()
        cb_data = EventActionCallback(action="complete", event_id="e1")
        with ctx:
            await handler.callback(q, cb_data)
        svc.calendar.calendar_repo.mark_completed.assert_awaited()
        q.answer.assert_awaited()

    async def test_no_message(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["event_action_handler"]

        q = make_callback_query()
        q.message = None
        cb_data = EventActionCallback(action="snooze", event_id="e1")
        with ctx:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited()


class TestPageCallback:
    async def test_page(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "callback_query")
        handler = handlers["page_handler"]

        q = make_callback_query()
        cb_data = PageCallback(screen="events", page=2)
        with ctx:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited()
