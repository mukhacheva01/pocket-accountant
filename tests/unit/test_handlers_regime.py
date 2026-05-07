"""Tests for regime selection FSM handlers in bot.handlers."""

from bot.handlers import build_router
from tests.unit.bot_helpers import make_message, make_state, patch_handler_deps


class TestRegimeActivityHandler:
    async def test_valid_activity(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_activity_handler"]

        msg = make_message("Услуги")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(activity="services")

    async def test_invalid_activity(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_activity_handler"]

        msg = make_message("Неизвестное")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "кнопок" in msg.answer.call_args[0][0].lower()


class TestRegimeIncomeHandler:
    async def test_valid_income(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_income_handler"]

        msg = make_message("300000")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited()

    async def test_invalid_income(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_income_handler"]

        msg = make_message("abc")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "сумму" in msg.answer.call_args[0][0].lower()


class TestRegimeEmployeesHandler:
    async def test_yes(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_employees_handler"]

        msg = make_message("Да")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(has_employees=True)

    async def test_invalid(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_employees_handler"]

        msg = make_message("Не знаю")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestRegimeCounterpartiesHandler:
    async def test_valid(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_counterparties_handler"]

        msg = make_message("Физлица")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(counterparties="individuals")

    async def test_invalid(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_counterparties_handler"]

        msg = make_message("Все")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestRegimeRegionHandler:
    async def test_valid_completion(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_region_handler"]

        msg = make_message("Москва")
        state = make_state(data={
            "activity": "services",
            "monthly_income": "300000",
            "has_employees": False,
            "counterparties": "individuals",
        })
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        mc.compare_regimes.assert_awaited()
        msg.answer.assert_awaited()

    async def test_missing_data(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_region_handler"]

        msg = make_message("Москва")
        state = make_state(data={})
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        msg.answer.assert_awaited()
        assert "заново" in msg.answer.call_args[0][0].lower() or "/regime" in msg.answer.call_args[0][0]
