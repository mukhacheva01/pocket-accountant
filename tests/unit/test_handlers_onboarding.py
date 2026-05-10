"""Tests for onboarding FSM handlers in bot.handlers."""

from bot.handlers import build_router
from tests.unit.bot_helpers import make_message, make_state, patch_backend_client


class TestOnboardingEntityType:
    async def test_ip_selected(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("ИП")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.update_data.assert_awaited()
        state.set_state.assert_awaited()

    async def test_self_employed_skips_tax(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("Самозанятый")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        calls = [c[1] for c in state.update_data.call_args_list]
        tax_set = any("tax_regime" in kw for kw in calls)
        assert tax_set

    async def test_planned_entity(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("Пока не открыт")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.update_data.assert_awaited()

    async def test_invalid_entity(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_entity_handler"]

        msg = make_message("Неизвестно")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "кнопок" in msg.answer.call_args[0][0].lower()


class TestOnboardingTaxRegime:
    async def test_usn_selected(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_tax_handler"]

        msg = make_message("УСН 6%")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.update_data.assert_awaited()

    async def test_invalid_tax(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_tax_handler"]

        msg = make_message("Неизвестный режим")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "режим" in msg.answer.call_args[0][0].lower()


class TestOnboardingEmployees:
    async def test_yes(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_employees_handler"]

        msg = make_message("Да")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.update_data.assert_awaited()

    async def test_no(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_employees_handler"]

        msg = make_message("Нет")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        state.update_data.assert_awaited()

    async def test_invalid(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_employees_handler"]

        msg = make_message("Может быть")
        state = make_state()
        with bc_patch:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestOnboardingFinish:
    async def test_complete(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_finish_handler"]

        msg = make_message("Москва")
        state = make_state(data={
            "entity_type": "ip",
            "tax_regime": "usn_income",
            "has_employees": False,
        })
        with bc_patch:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        mc.onboarding_with_sync.assert_awaited()

    async def test_missing_entity_type(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_finish_handler"]

        msg = make_message("Москва")
        state = make_state(data={})
        with bc_patch:
            await handler.callback(msg, state)
        state.clear.assert_awaited()
        msg.answer.assert_awaited()
        assert "заново" in msg.answer.call_args[0][0].lower() or "/start" in msg.answer.call_args[0][0]

    async def test_defaults_tax_to_npd(self):
        bc_patch, mc = patch_backend_client()
        with bc_patch:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["onboarding_finish_handler"]

        msg = make_message("Москва")
        state = make_state(data={
            "entity_type": "self_employed",
        })
        with bc_patch:
            await handler.callback(msg, state)
        mc.onboarding_with_sync.assert_awaited()
