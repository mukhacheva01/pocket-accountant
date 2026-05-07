"""Tests for onboarding FSM handlers in bot.handlers."""

from shared.db.enums import EntityType, TaxRegime
from bot.handlers import build_router
from tests.unit.bot_helpers import make_message, make_state, patch_handler_deps


class TestOnboardingEntityType:
    async def test_ip_selected(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("ИП")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR.value)
        state.set_state.assert_awaited()

    async def test_self_employed_skips_tax(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("Самозанятый")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        calls = [c[1] for c in state.update_data.call_args_list]
        tax_set = any("tax_regime" in kw for kw in calls)
        assert tax_set

    async def test_planned_entity(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("Пока не открыт")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(planning_entity=True)

    async def test_invalid_entity(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("Неизвестно")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "кнопок" in msg.answer.call_args[0][0].lower()


class TestOnboardingTaxRegime:
    async def test_usn_selected(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_tax_handler"]

        msg = make_message("УСН 6%")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(tax_regime=TaxRegime.USN_INCOME.value)

    async def test_invalid_tax(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_tax_handler"]

        msg = make_message("Неизвестный режим")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "режим" in msg.answer.call_args[0][0].lower()


class TestOnboardingEmployees:
    async def test_yes(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_employees_handler"]

        msg = make_message("Да")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(has_employees=True)

    async def test_no(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_employees_handler"]

        msg = make_message("Нет")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.update_data.assert_awaited_with(has_employees=False)

    async def test_invalid(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_employees_handler"]

        msg = make_message("Может быть")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestOnboardingFinish:
    async def test_complete(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_finish_handler"]

        msg = make_message("Москва")
        state = make_state(data={
            "entity_type": EntityType.INDIVIDUAL_ENTREPRENEUR.value,
            "tax_regime": TaxRegime.USN_INCOME.value,
            "has_employees": False,
        })
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        mc.complete_onboarding_full.assert_awaited()

    async def test_missing_entity_type(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_finish_handler"]

        msg = make_message("Москва")
        state = make_state(data={})
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        msg.answer.assert_awaited()
        assert "заново" in msg.answer.call_args[0][0].lower() or "/start" in msg.answer.call_args[0][0]

    async def test_defaults_tax_to_npd(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_finish_handler"]

        msg = make_message("Москва")
        state = make_state(data={
            "entity_type": EntityType.SELF_EMPLOYED.value,
        })
        with cl_p, gs_p:
            await handler.callback(msg, state)
        mc.complete_onboarding_full.assert_awaited()
