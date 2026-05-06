"""Tests for AI consult and catch-all handlers in bot.handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

from shared.db.enums import FinanceRecordType
from bot.handlers import build_router
from tests.unit.bot_helpers import make_message, make_state, make_services


MODULE = "bot.handlers"


def _patch_deps(services=None):
    svc = services or make_services()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)
    sf_patch = patch(f"{MODULE}.SessionFactory", return_value=session)
    bs_patch = patch(f"{MODULE}.build_services", return_value=svc)
    gs_patch = patch(f"{MODULE}.get_settings", return_value=MagicMock(
        stars_price_basic=150, stars_price_pro=400, stars_price_annual=3500,
    ))
    return sf_patch, bs_patch, gs_patch, svc, session


class TestAIConsultHandler:
    async def test_enter_consult(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_handler"]

        msg = make_message("/consult")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()
        msg.answer.assert_awaited()

    async def test_paywall_blocks(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        svc.subscription.can_use_ai = AsyncMock(return_value=(False, 0))
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_handler"]

        msg = make_message("/consult")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestAIConsultChattingHandler:
    async def test_ai_question(self):
        sf_p, bs_p, gs_p, svc, session = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("Как рассчитать налог?")
        state = make_state()
        with sf_p, bs_p, gs_p, patch(f"{MODULE}.allow_ai_request", AsyncMock(return_value=True)):
            await handler.callback(msg, state)
        msg.answer.assert_awaited()

    async def test_empty_message(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_home_button_exits(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("🏠 Главная")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()

    async def test_other_menu_button_exits(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("📊 Финансы")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_awaited()

    async def test_consult_button_stays(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("💬 AI Консультация")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.clear.assert_not_awaited()

    async def test_rate_limited(self):
        sf_p, bs_p, gs_p, svc, session = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("Как рассчитать налог?")
        state = make_state()
        with sf_p, bs_p, gs_p, patch(f"{MODULE}.allow_ai_request", AsyncMock(return_value=False)):
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "много запросов" in msg.answer.call_args[0][0].lower() or "подожди" in msg.answer.call_args[0][0].lower()

    async def test_paywall_in_chatting(self):
        sf_p, bs_p, gs_p, svc, session = _patch_deps()
        svc.subscription.can_use_ai = AsyncMock(return_value=(False, 0))
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_consult_chatting_handler"]

        msg = make_message("Как рассчитать налог?")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()


class TestClearAIHistoryHandler:
    async def test_clear(self):
        sf_p, bs_p, gs_p, svc, session = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["clear_ai_history_handler"]

        msg = make_message("🗑 Новый диалог")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        state.set_state.assert_awaited()
        msg.answer.assert_awaited()


class TestCatchAllHandler:
    async def test_with_state_returns(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("что-то")
        state = make_state(current_state="SomeState")
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_menu_button_ignored(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("🏠 Главная")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_empty_returns(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_not_awaited()

    async def test_finance_hint_saves(self):
        from decimal import Decimal
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        record = MagicMock()
        record.record_type = FinanceRecordType.INCOME
        record.amount = Decimal("50000")
        record.category = "services"
        svc.finance.add_from_text = AsyncMock(return_value=record)

        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("получил 50000 от клиента")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "Сохранил" in msg.answer.call_args[0][0] or "сохранил" in msg.answer.call_args[0][0].lower()

    async def test_finance_parse_error_falls_through(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        svc.finance.add_from_text = AsyncMock(side_effect=ValueError("bad"))
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("получил что-то")
        state = make_state()
        with sf_p, bs_p, gs_p, patch(f"{MODULE}.allow_ai_request", AsyncMock(return_value=True)):
            await handler.callback(msg, state)
        msg.answer.assert_awaited()

    async def test_template_match(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        svc.templates.match_template = MagicMock(return_value="Шаблон: Акт выполненных работ")
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("акт выполненных работ")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "Акт" in msg.answer.call_args[0][0] or "Шаблон" in msg.answer.call_args[0][0]

    async def test_ai_paywall(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        svc.subscription.can_use_ai = AsyncMock(return_value=(False, 0))
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("что такое НДС?")
        state = make_state()
        with sf_p, bs_p, gs_p:
            await handler.callback(msg, state)
        msg.answer.assert_awaited()

    async def test_ai_rate_limited(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("что такое НДС?")
        state = make_state()
        with sf_p, bs_p, gs_p, patch(f"{MODULE}.allow_ai_request", AsyncMock(return_value=False)):
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        assert "подожди" in msg.answer.call_args[0][0].lower() or "много" in msg.answer.call_args[0][0].lower()

    async def test_ai_answer(self):
        sf_p, bs_p, gs_p, svc, session = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["ai_question_handler"]

        msg = make_message("что такое НДС?")
        state = make_state()
        with sf_p, bs_p, gs_p, patch(f"{MODULE}.allow_ai_request", AsyncMock(return_value=True)):
            await handler.callback(msg, state)
        msg.answer.assert_awaited()
        svc.ai.answer_tax_question.assert_awaited()


class TestPreCheckoutHandler:
    async def test_valid(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.pre_checkout_query.handlers}
        handler = handlers["pre_checkout_handler"]

        pre = AsyncMock()
        pre.invoice_payload = "sub_basic"
        pre.total_amount = 150
        pre.answer = AsyncMock()
        with sf_p, bs_p, gs_p:
            await handler.callback(pre)
        pre.answer.assert_awaited_with(ok=True)

    async def test_invalid_payload(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.pre_checkout_query.handlers}
        handler = handlers["pre_checkout_handler"]

        pre = AsyncMock()
        pre.invoice_payload = "unknown"
        pre.total_amount = 100
        pre.answer = AsyncMock()
        with sf_p, bs_p, gs_p:
            await handler.callback(pre)
        pre.answer.assert_awaited()
        assert pre.answer.call_args[1].get("ok") is False or pre.answer.call_args[0][0] is False

    async def test_wrong_amount(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.pre_checkout_query.handlers}
        handler = handlers["pre_checkout_handler"]

        pre = AsyncMock()
        pre.invoice_payload = "sub_basic"
        pre.total_amount = 999
        pre.answer = AsyncMock()
        with sf_p, bs_p, gs_p:
            await handler.callback(pre)
        assert pre.answer.call_args[1].get("ok") is False or pre.answer.call_args[0][0] is False


class TestSuccessfulPaymentHandler:
    async def test_successful(self):
        from datetime import datetime
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        sub = MagicMock()
        sub.expires_at = datetime(2026, 8, 1)
        svc.subscription.activate = AsyncMock(return_value=sub)

        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["successful_payment_handler"]

        msg = make_message("")
        msg.successful_payment = MagicMock()
        msg.successful_payment.invoice_payload = "sub_basic"
        msg.successful_payment.total_amount = 150
        msg.successful_payment.telegram_payment_charge_id = "charge_123"
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        svc.subscription.activate.assert_awaited()
        msg.answer.assert_awaited()

    async def test_unknown_plan(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["successful_payment_handler"]

        msg = make_message("")
        msg.successful_payment = MagicMock()
        msg.successful_payment.invoice_payload = "unknown_plan"
        msg.successful_payment.total_amount = 100
        msg.successful_payment.telegram_payment_charge_id = "charge_456"
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "поддержку" in msg.answer.call_args[0][0].lower()

    async def test_duplicate_payment(self):
        sf_p, bs_p, gs_p, svc, _ = _patch_deps()
        svc.subscription.payment_exists = AsyncMock(return_value=True)
        with sf_p, bs_p, gs_p:
            router = build_router()
        handlers = {h.callback.__name__: h for h in router.message.handlers}
        handler = handlers["successful_payment_handler"]

        msg = make_message("")
        msg.successful_payment = MagicMock()
        msg.successful_payment.invoice_payload = "sub_basic"
        msg.successful_payment.total_amount = 150
        msg.successful_payment.telegram_payment_charge_id = "charge_dup"
        with sf_p, bs_p, gs_p:
            await handler.callback(msg)
        msg.answer.assert_awaited()
        assert "обработана" in msg.answer.call_args[0][0].lower()
