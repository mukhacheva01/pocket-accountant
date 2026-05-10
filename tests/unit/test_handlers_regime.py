"""Tests for regime selection FSM handlers in bot.handlers."""

from bot.handlers import build_router
from tests.unit.bot_helpers import make_message, make_state, patch_backend_client


class TestRegimeHandler:
    async def test_enter_regime(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_handler"]

        msg = make_message("/regime")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()
        msg.answer.assert_awaited()


class TestRegimeActivityHandler:
    async def test_valid_activity(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_activity_handler"]

        msg = make_message("Услуги")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.update_data.assert_awaited()
        state.set_state.assert_awaited()

    async def test_invalid_activity(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_activity_handler"]

        msg = make_message("Неизвестная деятельность")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        state.update_data.assert_not_awaited()


class TestRegimeIncomeHandler:
    async def test_valid_income(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_income_handler"]

        msg = make_message("300000")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.update_data.assert_awaited()
        state.set_state.assert_awaited()

    async def test_invalid_income(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_income_handler"]

        msg = make_message("не число")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        state.update_data.assert_not_awaited()


class TestRegimeEmployeesHandler:
    async def test_yes(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_employees_handler"]

        msg = make_message("Да")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.update_data.assert_awaited()


class TestRegimeCounterpartiesHandler:
    async def test_valid(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_counterparties_handler"]

        msg = make_message("Физлица")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.update_data.assert_awaited()


class TestRegimeRegionHandler:
    async def test_finish(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_region_handler"]

        msg = make_message("Москва")
        state = make_state(data={"activity": "services", "monthly_income": "300000",
                                  "has_employees": False, "counterparties": "mixed"})
        with bc_patch:
            await handler.callback(msg, state)
        mc.compare_regimes.assert_awaited()
        state.clear.assert_awaited()
        msg.answer.assert_awaited()
