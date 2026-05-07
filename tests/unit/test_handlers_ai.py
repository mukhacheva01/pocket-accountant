"""Tests for AI consult and catch-all handlers in bot.handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

from shared.db.enums import FinanceRecordType
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


class TestAIConsultHandler:
    async def test_enter_consult(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_consult_handler"]

        msg = make_message("/consult")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()
        msg.answer.assert_awaited()

    async def test_paywall_blocks(self):
        ctx, svc, _, router = _build()
        svc.subscription.can_use_ai = AsyncMock(return_value=(False, 0))
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_consult_handler"]

        msg = make_message("/consult")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestAIConsultChattingHandler:
    async def test_ai_question(self):
        ctx, svc, session, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("Как рассчитать налог?")
        state = make_state()
        with ctx, patch("backend.services.rate_limit.allow_ai_request", AsyncMock(return_value=True)), patch("bot.handlers.navigation.allow_ai_request", AsyncMock(return_value=True)):
            await handler.callback(msg, state)
        msg.answer.assert_awaited()

    async def test_empty_message(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_home_button_exits(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("🏠 Главная")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        state.clear.assert_awaited()

    async def test_other_menu_button_exits(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("📊 Финансы")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        state.clear.assert_awaited()

    async def test_consult_button_stays(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("💬 AI Консультация")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        state.clear.assert_not_awaited()

    async def test_rate_limited(self):
        ctx, svc, session, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("Как рассчитать налог?")
        state = make_state()
        with ctx, patch("backend.services.rate_limit.allow_ai_request", AsyncMock(return_value=False)), patch("bot.handlers.navigation.allow_ai_request", AsyncMock(return_value=False)):
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "много запросов" in msg.answer.call_args[0][0].lower() or "подожди" in msg.answer.call_args[0][0].lower()

    async def test_paywall_in_chatting(self):
        ctx, svc, session, router = _build()
        svc.subscription.can_use_ai = AsyncMock(return_value=(False, 0))
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("Как рассчитать налог?")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestClearAIHistoryHandler:
    async def test_clear(self):
        ctx, svc, session, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["clear_ai_history_handler"]

        msg = make_message("🗑 Новый диалог")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()
        msg.answer.assert_awaited()


class TestCatchAllHandler:
    async def test_with_state_returns(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_question_handler"]

        msg = make_message("что-то")
        state = make_state(current_state="SomeState")
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_menu_button_ignored(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_question_handler"]

        msg = make_message("🏠 Главная")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_empty_returns(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_question_handler"]

        msg = make_message("")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_finance_hint_saves(self):
        from decimal import Decimal
        ctx, svc, _, router = _build()
        record = MagicMock()
        record.record_type = FinanceRecordType.INCOME
        record.amount = Decimal("50000")
        record.category = "services"
        svc.finance.add_from_text = AsyncMock(return_value=record)

        handlers = collect_handlers(router, "message")
        handler = handlers["ai_question_handler"]

        msg = make_message("получил 50000 от клиента")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "Сохранил" in msg.answer.call_args[0][0] or "сохранил" in msg.answer.call_args[0][0].lower()

    async def test_finance_parse_error_falls_through(self):
        ctx, svc, _, router = _build()
        svc.finance.add_from_text = AsyncMock(side_effect=ValueError("bad"))
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_question_handler"]

        msg = make_message("получил что-то")
        state = make_state()
        with ctx, patch("backend.services.rate_limit.allow_ai_request", AsyncMock(return_value=True)), patch("bot.handlers.navigation.allow_ai_request", AsyncMock(return_value=True)):
            await handler.callback(msg, state)
        msg.answer.assert_awaited()

    async def test_template_match(self):
        ctx, svc, _, router = _build()
        svc.templates.match_template = MagicMock(return_value="Шаблон: Акт выполненных работ")
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_question_handler"]

        msg = make_message("акт выполненных работ")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "Акт" in msg.answer.call_args[0][0] or "Шаблон" in msg.answer.call_args[0][0]

    async def test_ai_paywall(self):
        ctx, svc, _, router = _build()
        svc.subscription.can_use_ai = AsyncMock(return_value=(False, 0))
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_question_handler"]

        msg = make_message("что такое НДС?")
        state = make_state()
        with ctx:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()

    async def test_ai_rate_limited(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_question_handler"]

        msg = make_message("что такое НДС?")
        state = make_state()
        with ctx, patch("backend.services.rate_limit.allow_ai_request", AsyncMock(return_value=False)), patch("bot.handlers.navigation.allow_ai_request", AsyncMock(return_value=False)):
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "подожди" in msg.answer.call_args[0][0].lower() or "много" in msg.answer.call_args[0][0].lower()

    async def test_ai_answer(self):
        ctx, svc, session, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["ai_question_handler"]

        msg = make_message("что такое НДС?")
        state = make_state()
        with ctx, patch("backend.services.rate_limit.allow_ai_request", AsyncMock(return_value=True)), patch("bot.handlers.navigation.allow_ai_request", AsyncMock(return_value=True)):
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        svc.ai.answer_tax_question.assert_awaited()


class TestPreCheckoutHandler:
    async def test_valid(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "pre_checkout_query")
        handler = handlers["pre_checkout_handler"]

        pre = AsyncMock()
        pre.invoice_payload = "sub_basic"
        pre.total_amount = 150
        pre.answer = AsyncMock()
        with ctx:
            await handler.callback(pre)
        pre.answer.assert_awaited_with(ok=True)

    async def test_invalid_payload(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "pre_checkout_query")
        handler = handlers["pre_checkout_handler"]

        pre = AsyncMock()
        pre.invoice_payload = "unknown"
        pre.total_amount = 100
        pre.answer = AsyncMock()
        with ctx:
            await handler.callback(pre)
        pre.answer.assert_awaited()
        assert pre.answer.call_args[1].get("ok") is False or pre.answer.call_args[0][0] is False

    async def test_wrong_amount(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "pre_checkout_query")
        handler = handlers["pre_checkout_handler"]

        pre = AsyncMock()
        pre.invoice_payload = "sub_basic"
        pre.total_amount = 999
        pre.answer = AsyncMock()
        with ctx:
            await handler.callback(pre)
        assert pre.answer.call_args[1].get("ok") is False or pre.answer.call_args[0][0] is False


class TestSuccessfulPaymentHandler:
    async def test_successful(self):
        from datetime import datetime
        ctx, svc, _, router = _build()
        sub = MagicMock()
        sub.expires_at = datetime(2026, 8, 1)
        svc.subscription.activate = AsyncMock(return_value=sub)

        handlers = collect_handlers(router, "message")
        handler = handlers["successful_payment_handler"]

        msg = make_message("")
        msg.successful_payment = MagicMock()
        msg.successful_payment.invoice_payload = "sub_basic"
        msg.successful_payment.total_amount = 150
        msg.successful_payment.telegram_payment_charge_id = "charge_123"
        with ctx:
            await handler.callback(msg)
        svc.subscription.activate.assert_awaited()
        msg.answer.assert_awaited()

    async def test_unknown_plan(self):
        ctx, svc, _, router = _build()
        handlers = collect_handlers(router, "message")
        handler = handlers["successful_payment_handler"]

        msg = make_message("")
        msg.successful_payment = MagicMock()
        msg.successful_payment.invoice_payload = "unknown_plan"
        msg.successful_payment.total_amount = 100
        msg.successful_payment.telegram_payment_charge_id = "charge_456"
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "поддержку" in msg.answer.call_args[0][0].lower()

    async def test_duplicate_payment(self):
        ctx, svc, _, router = _build()
        svc.subscription.payment_exists = AsyncMock(return_value=True)
        handlers = collect_handlers(router, "message")
        handler = handlers["successful_payment_handler"]

        msg = make_message("")
        msg.successful_payment = MagicMock()
        msg.successful_payment.invoice_payload = "sub_basic"
        msg.successful_payment.total_amount = 150
        msg.successful_payment.telegram_payment_charge_id = "charge_dup"
        with ctx:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "обработана" in msg.answer.call_args[0][0].lower()
