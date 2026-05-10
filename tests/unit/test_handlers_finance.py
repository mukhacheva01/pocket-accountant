"""Tests for finance input FSM handlers in bot.handlers."""

from unittest.mock import AsyncMock

from bot.handlers import build_router
from tests.unit.bot_helpers import make_message, make_state, patch_backend_client


class TestAddIncomeHandler:
    async def test_no_payload_prompts(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["add_income_handler"]

        msg = make_message("/add_income")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()

    async def test_with_payload_saves(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["add_income_handler"]

        msg = make_message("/add_income получил 50000 от клиента")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        mc.add_from_text.assert_awaited()
        msg.answer.assert_awaited()
        assert "сохранён" in msg.answer.call_args[0][0].lower()

    async def test_invalid_format(self):
        bc_patch, mc = patch_backend_client()
        mc.add_from_text = AsyncMock(return_value={"ok": False})
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["add_income_handler"]

        msg = make_message("/add_income что-то непонятное")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "формат" in msg.answer.call_args[0][0].lower()


class TestAddExpenseHandler:
    async def test_no_payload_prompts(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["add_expense_handler"]

        msg = make_message("/add_expense")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()

    async def test_with_payload_saves(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["add_expense_handler"]

        msg = make_message("/add_expense заплатил 12000 за рекламу")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        mc.add_from_text.assert_awaited()
        assert "сохранён" in msg.answer.call_args[0][0].lower()


class TestIncomeStateHandler:
    async def test_valid_income(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["income_state_handler"]

        msg = make_message("получил 50000 от клиента")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        mc.add_from_text.assert_awaited()
        state.clear.assert_awaited()

    async def test_empty_text(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["income_state_handler"]

        msg = make_message("")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "сумму" in msg.answer.call_args[0][0].lower()

    async def test_parse_error(self):
        bc_patch, mc = patch_backend_client()
        mc.add_from_text = AsyncMock(return_value={"ok": False})
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["income_state_handler"]

        msg = make_message("не понятно")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestExpenseStateHandler:
    async def test_valid_expense(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["expense_state_handler"]

        msg = make_message("заплатил 12000 за рекламу")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        mc.add_from_text.assert_awaited()
        state.clear.assert_awaited()

    async def test_empty_text(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["expense_state_handler"]

        msg = make_message("")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "сумму" in msg.answer.call_args[0][0].lower()
