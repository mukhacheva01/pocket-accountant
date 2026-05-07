"""Tests for finance input FSM handlers in bot.handlers."""

from unittest.mock import AsyncMock, MagicMock

from bot.handlers import build_router
from tests.unit.bot_helpers import (
    collect_handlers,
    make_message,
    make_state,
    make_services,
    patch_handler_deps,
)


def _build(services=None):
    ctx, svc, session = patch_handler_deps(services)
    with ctx:
        router = build_router()
    return ctx, svc, session, router


class TestAddIncomeHandler:
    async def test_no_payload_prompts(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["add_income_handler"]

        msg = make_message("/add_income")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()

    async def test_with_payload_saves(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["add_income_handler"]

        msg = make_message("/add_income получил 50000 от клиента")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        svc.finance.add_from_text.assert_awaited()
        msg.answer.assert_awaited()
        assert "сохранён" in msg.answer.call_args[0][0].lower()

    async def test_invalid_format(self):
        ctx, svc, _, router = _build()
        svc.finance.add_from_text = AsyncMock(side_effect=ValueError("bad"))
        handlers = collect_handlers(router, "message")
        handler = handlers["add_income_handler"]

        msg = make_message("/add_income что-то непонятное")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "формат" in msg.answer.call_args[0][0].lower()


class TestAddExpenseHandler:
    async def test_no_payload_prompts(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["add_expense_handler"]

        msg = make_message("/add_expense")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()

    async def test_with_payload_saves(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["add_expense_handler"]

        msg = make_message("/add_expense заплатил 12000 за рекламу")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        svc.finance.add_from_text.assert_awaited()
        assert "сохранён" in msg.answer.call_args[0][0].lower()


class TestIncomeStateHandler:
    async def test_valid_income(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["income_state_handler"]

        msg = make_message("получил 50000 от клиента")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        svc.finance.add_from_text.assert_awaited()
        state.clear.assert_awaited()

    async def test_empty_text(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["income_state_handler"]

        msg = make_message("")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "сумму" in msg.answer.call_args[0][0].lower()

    async def test_parse_error(self):
        ctx, svc, _, router = _build()
        svc.finance.add_from_text = AsyncMock(side_effect=ValueError("bad"))
        handlers = collect_handlers(router, "message")
        handler = handlers["income_state_handler"]

        msg = make_message("abc")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "сумму" in msg.answer.call_args[0][0].lower()


class TestExpenseStateHandler:
    async def test_valid_expense(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["expense_state_handler"]

        msg = make_message("заплатил 12000 за рекламу")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        svc.finance.add_from_text.assert_awaited()
        state.clear.assert_awaited()

    async def test_empty_text(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["expense_state_handler"]

        msg = make_message("")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
