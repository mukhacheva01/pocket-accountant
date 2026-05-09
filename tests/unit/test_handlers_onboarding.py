"""Tests for onboarding FSM handlers in bot.handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

from shared.db.enums import EntityType, TaxRegime
from bot.handlers import build_router
from tests.unit.bot_helpers import make_message, make_state, make_services


MODULE = "bot.handlers.helpers"


def _patch_deps(services=None):
    svc = services or make_services()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    sf_patch = patch(f"{MODULE}.SessionFactory", return_value=session)
    bs_patch = patch(f"{MODULE}.build_services", return_value=svc)
    gs_patch = patch(f"{MODULE}.get_settings", return_value=MagicMock(
        stars_price_basic=150, stars_price_pro=400, stars_price_annual=3500,
    ))
    return sf_patch, bs_patch, gs_patch, svc, session


class TestOnboardingEntityType:
    async def test_ip_selected(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("ИП")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR.value)
        state.set_state.assert_awaited()

    async def test_self_employed_skips_tax(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("Самозанятый")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        calls = [c[1] for c in state.update_data.call_args_list]
        tax_set = any("tax_regime" in kw for kw in calls)
        assert tax_set

    async def test_planned_entity(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("Пока не открыт")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(planning_entity=True)

    async def test_invalid_entity(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("Неизвестно")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "кнопок" in msg.answer.call_args[0][0].lower()


class TestOnboardingTaxRegime:
    async def test_usn_selected(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_tax_handler"]

        msg = make_message("УСН 6%")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(tax_regime=TaxRegime.USN_INCOME.value)

    async def test_invalid_tax(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_tax_handler"]

        msg = make_message("Неизвестный режим")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "режим" in msg.answer.call_args[0][0].lower()


class TestOnboardingEmployees:
    async def test_yes(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_employees_handler"]

        msg = make_message("Да")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(has_employees=True)

    async def test_no(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_employees_handler"]

        msg = make_message("Нет")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(has_employees=False)

    async def test_invalid(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_employees_handler"]

        msg = make_message("Может быть")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestOnboardingFinish:
    async def test_complete(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_finish_handler"]

        msg = make_message("Москва")
        state = make_state(data={
            "entity_type": EntityType.INDIVIDUAL_ENTREPRENEUR.value,
            "tax_regime": TaxRegime.USN_INCOME.value,
            "has_employees": False,
        })
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        svc.onboarding.save_profile.assert_awaited()

    async def test_missing_entity_type(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_finish_handler"]

        msg = make_message("Москва")
        state = make_state(data={})
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        msg.answer.assert_awaited()
        assert "заново" in msg.answer.call_args[0][0].lower() or "/start" in msg.answer.call_args[0][0]

    async def test_defaults_tax_to_npd(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_finish_handler"]

        msg = make_message("Москва")
        state = make_state(data={
            "entity_type": EntityType.SELF_EMPLOYED.value,
        })
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        svc.onboarding.save_profile.assert_awaited()
