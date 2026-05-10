"""Tests for AI consult and catch-all handlers in bot.handlers."""

from unittest.mock import AsyncMock

from bot.handlers import build_router
from tests.unit.bot_helpers import make_message, make_state, patch_backend_client


class TestAIConsultHandler:
    async def test_enter_consult(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_handler"]

        msg = make_message("/consult")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()
        msg.answer.assert_awaited()

    async def test_paywall_blocks(self):
        bc_patch, mc = patch_backend_client()
        mc.get_subscription_status = AsyncMock(return_value={
            "is_active": False, "can_ai": False, "remaining_ai": 0,
            "prices": {"basic": 150, "pro": 400, "annual": 3500},
        })
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_handler"]

        msg = make_message("/consult")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestAIConsultChattingHandler:
    async def test_ai_question(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}

        msg = make_message("Как рассчитать налог?")
        state = make_state()
        with bc_patch:
            handler = handlers.get("ai_chatting_handler")
            if handler:
                await handler.callback(msg, state)
                msg.answer.assert_awaited()

    async def test_home_button_exits(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}

        msg = make_message("🏠 Главная")
        state = make_state()
        with bc_patch:
            handler = handlers.get("ai_chatting_handler")
            if handler:
                await handler.callback(msg, state)
                state.clear.assert_awaited()


class TestCatchAllHandler:
    async def test_finance_catch(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers.get("ai_question_handler")
        if handler is None:
            return

        msg = make_message("получил 50000 от клиента")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()

    async def test_ai_catch(self):
        bc_patch, mc = patch_backend_client()
        mc.match_template = AsyncMock(return_value={"matched": False})
        mc.parse_and_calculate_tax = AsyncMock(return_value={"ok": False})
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers.get("ai_question_handler")
        if handler is None:
            return

        msg = make_message("Когда сдавать отчётность?")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
