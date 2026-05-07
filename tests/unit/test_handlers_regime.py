"""Tests for regime selection FSM handlers in bot.handlers."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from bot.handlers import build_router
from tests.unit.bot_helpers import (
    collect_handlers,
    make_message,
    make_state,
    patch_handler_deps,
)


def _build(services=None):
    ctx, svc, session = patch_handler_deps(services)
    with ctx:
        router = build_router()
    return ctx, svc, session, router


class TestRegimeActivityHandler:
    async def test_valid_activity(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["regime_activity_handler"]

        msg = make_message("Услуги")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(activity="services")

    async def test_invalid_activity(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["regime_activity_handler"]

        msg = make_message("Неизвестное")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "кнопок" in msg.answer.call_args[0][0].lower()


class TestRegimeIncomeHandler:
    async def test_valid_income(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["regime_income_handler"]

        with patch("bot.handlers.regime.TaxQueryParser") as mock_parser:
            mock_parser.parse_amount.return_value = Decimal("300000")
            msg = make_message("300000")
            state = make_state()
            with ctx:
                await handler.callback(msg, state)
        state.update_data.assert_awaited()

    async def test_invalid_income(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["regime_income_handler"]

        with patch("bot.handlers.regime.TaxQueryParser") as mock_parser:
            mock_parser.parse_amount.return_value = None
            msg = make_message("abc")
            state = make_state()
            with ctx:
                await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "сумму" in msg.answer.call_args[0][0].lower()


class TestRegimeEmployeesHandler:
    async def test_yes(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["regime_employees_handler"]

        msg = make_message("Да")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(has_employees=True)

    async def test_invalid(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["regime_employees_handler"]

        msg = make_message("Не знаю")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestRegimeCounterpartiesHandler:
    async def test_valid(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["regime_counterparties_handler"]

        msg = make_message("Физлица")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(counterparties="individuals")

    async def test_invalid(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["regime_counterparties_handler"]

        msg = make_message("Все")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestRegimeRegionHandler:
    async def test_valid_completion(self):
        ctx, svc, _, router = _build()
        compare_result = MagicMock()
        compare_result.render = MagicMock(return_value="Рекомендация: УСН 6%")
        svc.tax.compare_regimes = MagicMock(return_value=compare_result)

        handlers = collect_handlers(router, "message")
        handler = handlers["regime_region_handler"]

        msg = make_message("Москва")
        state = make_state(data={
            "activity": "services",
            "monthly_income": "300000",
            "has_employees": False,
            "counterparties": "individuals",
        })
        with ctx:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        msg.answer.assert_awaited()

    async def test_missing_data(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["regime_region_handler"]

        msg = make_message("Москва")
        state = make_state(data={})
        with ctx:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        msg.answer.assert_awaited()
        assert "заново" in msg.answer.call_args[0][0].lower() or "/regime" in msg.answer.call_args[0][0]
