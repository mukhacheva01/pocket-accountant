"""Tests for callback query handlers in bot.handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.callbacks import EventActionCallback, NavigationCallback, PageCallback, SubscriptionCallback
from bot.handlers import build_router
from tests.unit.bot_helpers import make_callback_query, make_state, patch_backend_client


NAV_TARGETS = [
    "home", "profile", "events", "finance", "help", "settings",
    "subscription", "calendar", "overdue", "documents", "laws",
    "reminders", "balance", "income_list", "expense_list", "referral",
]


class TestNavigationCallback:
    @pytest.mark.parametrize("target", NAV_TARGETS)
    async def test_nav_target(self, target):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target=target)
        state = make_state()
        with bc_patch:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_income_prompt(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="income_prompt")
        state = make_state()
        with bc_patch:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_expense_prompt(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="expense_prompt")
        state = make_state()
        with bc_patch:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_ai_consult(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_consult")
        state = make_state()
        with bc_patch:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_ai_clear_history(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_clear_history")
        state = make_state()
        with bc_patch:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()
        mc.ai_clear_history.assert_awaited()

    async def test_ai_exit(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_exit")
        state = make_state()
        with bc_patch:
            await handler.callback(q, cb_data, state)
        state.clear.assert_awaited()
        q.answer.assert_awaited()

    async def test_restart_onboarding(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="restart_onboarding")
        state = make_state()
        with bc_patch:
            await handler.callback(q, cb_data, state)
        state.set_state.assert_awaited()
        q.answer.assert_awaited()

    async def test_cancel_subscription(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="cancel_subscription")
        state = make_state()
        with bc_patch:
            await handler.callback(q, cb_data, state)
        mc.cancel_subscription.assert_awaited()
        q.answer.assert_awaited()

    async def test_ai_topic(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="ai_topic_calc")
        state = make_state()
        with bc_patch:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_unknown_target(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        cb_data = NavigationCallback(target="nonexistent")
        state = make_state()
        with bc_patch:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()

    async def test_no_message(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["navigation_handler"]

        q = make_callback_query()
        q.message = None
        cb_data = NavigationCallback(target="home")
        state = make_state()
        with bc_patch:
            await handler.callback(q, cb_data, state)
        q.answer.assert_awaited()


class TestPageCallback:
    async def test_page(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["page_handler"]

        q = make_callback_query()
        cb_data = PageCallback(page=2)
        with bc_patch:
            await handler.callback(q, cb_data)
        q.answer.assert_awaited()


class TestEventActionCallback:
    async def test_snooze(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["event_action_handler"]

        q = make_callback_query()
        cb_data = EventActionCallback(event_id="ev1", action="snooze")
        with bc_patch:
            await handler.callback(q, cb_data)
        mc.event_snooze.assert_awaited()
        q.answer.assert_awaited()

    async def test_complete(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["event_action_handler"]

        q = make_callback_query()
        cb_data = EventActionCallback(event_id="ev1", action="complete")
        with bc_patch:
            await handler.callback(q, cb_data)
        mc.event_complete.assert_awaited()
        q.answer.assert_awaited()


class TestSubscriptionCallback:
    async def test_buy_basic(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        cb_data = SubscriptionCallback(action="buy", plan="basic")
        with bc_patch, patch("shared.config.get_settings", return_value=MagicMock(
            stars_price_basic=150, stars_price_pro=400, stars_price_annual=3500,
        )):
            await handler.callback(q, cb_data)
        q.message.answer_invoice.assert_awaited()
        q.answer.assert_awaited()

    async def test_buy_unknown_plan(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.callback_query.handlers}
        handler = handlers["subscription_action_handler"]

        q = make_callback_query()
        cb_data = SubscriptionCallback(action="buy", plan="unknown")
        with bc_patch, patch("shared.config.get_settings", return_value=MagicMock(
            stars_price_basic=150, stars_price_pro=400, stars_price_annual=3500,
        )):
            await handler.callback(q, cb_data)
        q.answer.assert_awaited()


class TestUnsupportedContentHandler:
    async def test_sticker(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["unsupported_content_handler"]

        from tests.unit.bot_helpers import make_message
        msg = make_message("")
        msg.content_type = "sticker"
        with bc_patch:
            await handler.callback(msg)
        msg.answer.assert_awaited()
