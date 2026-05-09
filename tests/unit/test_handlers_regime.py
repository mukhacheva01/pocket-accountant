"""Tests for regime selection FSM handlers in bot.handlers."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from bot.handlers import build_router
from tests.unit.bot_helpers import make_message, make_state, make_services


MODULE = "bot.handlers.helpers"


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


class TestRegimeActivityHandler:
    async def test_valid_activity(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_activity_handler"]

        msg = make_message("Услуги")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(activity="services")

    async def test_invalid_activity(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_activity_handler"]

        msg = make_message("Неизвестное")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "кнопок" in msg.answer.call_args[0][0].lower()


class TestRegimeIncomeHandler:
    async def test_valid_income(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_income_handler"]

        with patch(f"{MODULE}.TaxQueryParser") as mock_parser:
            mock_parser.parse_amount.return_value = Decimal("300000")
            msg = make_message("300000")
            state = make_state()
            with sf_p, bs_p, gs_p:
                await handler.callback(msg, state)
        state.update_data.assert_awaited()

    async def test_invalid_income(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_income_handler"]

        with patch(f"{MODULE}.TaxQueryParser") as mock_parser:
            mock_parser.parse_amount.return_value = None
            msg = make_message("abc")
            state = make_state()
            with sf_p, bs_p, gs_p:
                await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "сумму" in msg.answer.call_args[0][0].lower()


class TestRegimeEmployeesHandler:
    async def test_yes(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_employees_handler"]

        msg = make_message("Да")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(has_employees=True)

    async def test_invalid(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_employees_handler"]

        msg = make_message("Не знаю")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestRegimeCounterpartiesHandler:
    async def test_valid(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_counterparties_handler"]

        msg = make_message("Физлица")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(counterparties="individuals")

    async def test_invalid(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_counterparties_handler"]

        msg = make_message("Все")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestRegimeRegionHandler:
    async def test_valid_completion(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        compare_result = MagicMock()
        compare_result.render = MagicMock(return_value="Рекомендация: УСН 6%")
        svc.tax.compare_regimes = MagicMock(return_value=compare_result)

        with sf_p, bs_p, gs_p:
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
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        msg.answer.assert_awaited()

    async def test_missing_data(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["regime_region_handler"]

        msg = make_message("Москва")
        state = make_state(data={})
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        msg.answer.assert_awaited()
        assert "заново" in msg.answer.call_args[0][0].lower() or "/regime" in msg.answer.call_args[0][0]
