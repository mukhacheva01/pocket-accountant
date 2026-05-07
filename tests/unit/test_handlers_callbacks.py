"""Tests for callback query handlers in bot.handlers."""

from unittest.mock import AsyncMock, MagicMock

from bot.callbacks import EventActionCallback, NavigationCallback, PageCallback, SubscriptionCallback
from bot.handlers import build_router
from tests.unit.bot_helpers import (
    make_callback_query,
    make_state,
    patch_handler_deps,
)


class TestNavigationCallback:
    async def test_home(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="home")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_profile(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="profile")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_events(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="events")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_finance(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="finance")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_help(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="help")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_settings(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="settings")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_subscription(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="subscription")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_calendar(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="calendar")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_overdue(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="overdue")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_documents(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="documents")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_laws(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="laws")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_reminders(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="reminders")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_balance(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="balance")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_income_list(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="income_list")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_expense_list(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="expense_list")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_income_prompt(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="income_prompt")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_expense_prompt(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="expense_prompt")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_referral(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        q.message.bot.me = AsyncMock(return_value=MagicMock(username="pocket121_accountant_bot"))
        cb_data = NavigationCallback(target="referral")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_ai_exit(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_exit")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        state.clear.assert_awaited()
        q.answer.assert_awaited()

    async def test_ai_clear_history(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_clear_history")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        mc.clear_ai_history.assert_awaited()
        q.answer.assert_awaited()

    async def test_restart_onboarding(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="restart_onboarding")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        state.clear.assert_awaited()
        q.answer.assert_awaited()

    async def test_cancel_subscription(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="cancel_subscription")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        mc.cancel_subscription.assert_awaited()
        q.answer.assert_awaited()

    async def test_unknown_target(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="nonexistent_page")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_no_message(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        q.message = None
        cb_data = NavigationCallback(target="home")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_ai_topic_shortcut(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_topic_calc")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()


class TestSubscriptionCallback:
    async def test_buy_basic(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message.answer_invoice = AsyncMock()
        cb_data = SubscriptionCallback(action="buy", plan="basic")
        with cl_p, gs_p:
            await handler.callback(q, cb_data)
        q.message.answer_invoice.assert_awaited()
        q.answer.assert_awaited()

    async def test_buy_pro(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message.answer_invoice = AsyncMock()
        cb_data = SubscriptionCallback(action="buy", plan="pro")
        with cl_p, gs_p:
            await handler.callback(q, cb_data)
        q.message.answer_invoice.assert_awaited()

    async def test_buy_annual(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message.answer_invoice = AsyncMock()
        cb_data = SubscriptionCallback(action="buy", plan="annual")
        with cl_p, gs_p:
            await handler.callback(q, cb_data)
        q.message.answer_invoice.assert_awaited()

    async def test_buy_unknown_plan(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        cb_data = SubscriptionCallback(action="buy", plan="unknown")
        with cl_p, gs_p:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited_with("Неизвестный тариф", show_alert=True)

    async def test_no_message(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        q.message = None
        cb_data = SubscriptionCallback(action="buy", plan="basic")
        with cl_p, gs_p:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited()


class TestEventActionCallback:
    async def test_snooze(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["event_action_handler"]

        q = make_callback_query()
        cb_data = EventActionCallback(action="snooze", event_id="e1")
        with cl_p, gs_p:
            await handler.callback(q, cb_data)
        mc.event_action.assert_awaited()
        q.answer.assert_awaited()

    async def test_complete(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["event_action_handler"]

        q = make_callback_query()
        cb_data = EventActionCallback(action="complete", event_id="e1")
        with cl_p, gs_p:
            await handler.callback(q, cb_data)
        mc.event_action.assert_awaited()
        q.answer.assert_awaited()

    async def test_no_message(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["event_action_handler"]

        q = make_callback_query()
        q.message = None
        cb_data = EventActionCallback(action="snooze", event_id="e1")
        with cl_p, gs_p:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited()


class TestPageCallback:
    async def test_page(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["page_handler"]

        q = make_callback_query()
        cb_data = PageCallback(screen="events", page=2)
        with cl_p, gs_p:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited()
