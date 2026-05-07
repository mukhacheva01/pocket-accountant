"""Tests for AI consult and catch-all handlers in bot.handlers."""

from unittest.mock import AsyncMock, MagicMock

from bot.handlers import build_router
from tests.unit.bot_helpers import (
    make_message,
    make_mock_client,
    make_state,
    patch_handler_deps,
)


class TestAIConsultHandler:
    async def test_enter_consult(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_handler"]

        msg = make_message("/consult")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()
        msg.answer.assert_awaited()

    async def test_paywall_blocks(self):
        mc = make_mock_client()
        mc.subscription_status = AsyncMock(return_value={
            "is_active": False, "remaining_ai_requests": 0, "can_use_ai": False,
        })
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_handler"]

        msg = make_message("/consult")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestAIConsultChattingHandler:
    async def test_ai_question(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("Как рассчитать налог?")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()

    async def test_empty_message(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_home_button_exits(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("🏠 Главная")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()

    async def test_other_menu_button_exits(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("📊 Финансы")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()

    async def test_consult_button_stays(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("💬 AI Консультация")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_not_awaited()

    async def test_paywall_in_chatting(self):
        mc = make_mock_client()
        mc.subscription_status = AsyncMock(return_value={
            "is_active": False, "remaining_ai_requests": 0, "can_use_ai": False,
        })
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("Как рассчитать налог?")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestClearAIHistoryHandler:
    async def test_clear(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["clear_ai_history_handler"]

        msg = make_message("🗑 Новый диалог")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        mc.clear_ai_history.assert_awaited()
        state.set_state.assert_awaited()
        msg.answer.assert_awaited()


class TestCatchAllHandler:
    async def test_with_state_returns(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("что-то")
        state = make_state(current_state="SomeState")
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_menu_button_ignored(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("🏠 Главная")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_empty_returns(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_finance_hint_saves(self):
        mc = make_mock_client()
        mc.add_finance_text = AsyncMock(return_value={"record": {
            "record_type": "income", "amount": "50000", "category": "services",
        }})
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("получил 50000 от клиента")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "Сохранил" in msg.answer.call_args[0][0] or "сохранил" in msg.answer.call_args[0][0].lower()

    async def test_finance_parse_error_falls_through(self):
        mc = make_mock_client()
        mc.add_finance_text = AsyncMock(side_effect=Exception("bad"))
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("получил что-то")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()

    async def test_template_match(self):
        mc = make_mock_client()
        mc.match_template = AsyncMock(return_value={"template": "Шаблон: Акт выполненных работ"})
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("акт выполненных работ")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "Акт" in msg.answer.call_args[0][0] or "Шаблон" in msg.answer.call_args[0][0]

    async def test_ai_paywall(self):
        mc = make_mock_client()
        mc.subscription_status = AsyncMock(return_value={
            "is_active": False, "remaining_ai_requests": 0, "can_use_ai": False,
        })
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("что такое НДС?")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()

    async def test_ai_answer(self):
        mc = make_mock_client()
        mc.parse_tax_query = AsyncMock(side_effect=Exception("no match"))
        mc.match_template = AsyncMock(return_value={"template": None})
        cl_p, gs_p, mc = patch_handler_deps(mc)
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("что такое НДС?")
        state = make_state()
        with cl_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        mc.ask_ai_with_history.assert_awaited()


class TestPreCheckoutHandler:
    async def test_valid(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.pre_checkout_query.handlers}
        handler = handlers["pre_checkout_handler"]

        pre = AsyncMock()
        pre.invoice_payload = "sub_basic"
        pre.total_amount = 150
        pre.answer = AsyncMock()
        with cl_p, gs_p:
            await handler.callback(pre)
        pre.answer.assert_awaited_with(ok=True)

    async def test_invalid_payload(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.pre_checkout_query.handlers}
        handler = handlers["pre_checkout_handler"]

        pre = AsyncMock()
        pre.invoice_payload = "unknown"
        pre.total_amount = 100
        pre.answer = AsyncMock()
        with cl_p, gs_p:
            await handler.callback(pre)
        pre.answer.assert_awaited()
        assert pre.answer.call_args[1].get("ok") is False or pre.answer.call_args[0][0] is False

    async def test_wrong_amount(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.pre_checkout_query.handlers}
        handler = handlers["pre_checkout_handler"]

        pre = AsyncMock()
        pre.invoice_payload = "sub_basic"
        pre.total_amount = 999
        pre.answer = AsyncMock()
        with cl_p, gs_p:
            await handler.callback(pre)
        assert pre.answer.call_args[1].get("ok") is False or pre.answer.call_args[0][0] is False


class TestSuccessfulPaymentHandler:
    async def test_successful(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["successful_payment_handler"]

        msg = make_message("")
        msg.successful_payment = MagicMock()
        msg.successful_payment.invoice_payload = "sub_basic"
        msg.successful_payment.total_amount = 150
        msg.successful_payment.telegram_payment_charge_id = "charge_123"
        with cl_p, gs_p:
            await handler.callback(msg)
        mc.activate_subscription.assert_awaited()
        mc.record_payment.assert_awaited()
        msg.answer.assert_awaited()

    async def test_unknown_plan(self):
        cl_p, gs_p, mc = patch_handler_deps()
        with cl_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["successful_payment_handler"]

        msg = make_message("")
        msg.successful_payment = MagicMock()
        msg.successful_payment.invoice_payload = "unknown_plan"
        msg.successful_payment.total_amount = 100
        msg.successful_payment.telegram_payment_charge_id = "charge_456"
        with cl_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "поддержку" in msg.answer.call_args[0][0].lower()
