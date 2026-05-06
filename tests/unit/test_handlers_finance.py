"""Tests for finance input FSM handlers in bot.handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers import build_router
from tests.unit.bot_helpers import make_message, make_state, make_services


MODULE = "bot.handlers"


def _patch_deps(services=None):
    svc = services or make_services()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.commit = AsyncMock()
    session.add = MagicMock()
    sf_patch = patch(f"{MODULE}.SessionFactory", return_value=session)
    bs_patch = patch(f"{MODULE}.build_services", return_value=svc)
    gs_patch = patch(f"{MODULE}.get_settings", return_value=MagicMock(
        stars_price_basic=150, stars_price_pro=400, stars_price_annual=3500,
    ))
    return sf_patch, bs_patch, gs_patch, svc, session


class TestAddIncomeHandler:
    async def test_no_payload_prompts(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["add_income_handler"]

        msg = make_message("/add_income")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()

    async def test_with_payload_saves(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["add_income_handler"]

        msg = make_message("/add_income получил 50000 от клиента")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        svc.finance.add_from_text.assert_awaited()
        msg.answer.assert_awaited()
        assert "сохранён" in msg.answer.call_args[0][0].lower()

    async def test_invalid_format(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        svc.finance.add_from_text = AsyncMock(side_effect=ValueError("bad"))
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["add_income_handler"]

        msg = make_message("/add_income что-то непонятное")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "формат" in msg.answer.call_args[0][0].lower()


class TestAddExpenseHandler:
    async def test_no_payload_prompts(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["add_expense_handler"]

        msg = make_message("/add_expense")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()

    async def test_with_payload_saves(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["add_expense_handler"]

        msg = make_message("/add_expense заплатил 12000 за рекламу")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        svc.finance.add_from_text.assert_awaited()
        assert "сохранён" in msg.answer.call_args[0][0].lower()


class TestIncomeStateHandler:
    async def test_valid_income(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["income_state_handler"]

        msg = make_message("получил 50000 от клиента")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        svc.finance.add_from_text.assert_awaited()
        state.clear.assert_awaited()

    async def test_empty_text(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["income_state_handler"]

        msg = make_message("")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "сумму" in msg.answer.call_args[0][0].lower()

    async def test_parse_error(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        svc.finance.add_from_text = AsyncMock(side_effect=ValueError("bad"))
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["income_state_handler"]

        msg = make_message("abc")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "сумму" in msg.answer.call_args[0][0].lower()


class TestExpenseStateHandler:
    async def test_valid_expense(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["expense_state_handler"]

        msg = make_message("заплатил 12000 за рекламу")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        svc.finance.add_from_text.assert_awaited()
        state.clear.assert_awaited()

    async def test_empty_text(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["expense_state_handler"]

        msg = make_message("")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
