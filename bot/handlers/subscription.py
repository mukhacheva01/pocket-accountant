"""Subscription handlers — Telegram Stars payments, pre-checkout, activation."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

import bot.handlers.helpers as _h
from bot.callbacks import SubscriptionCallback
from bot.keyboards import main_menu_keyboard
from bot.messages import payment_success_text

PLAN_DETAILS = {
    "basic": {"label": "Базовый", "days": 30},
    "pro": {"label": "Про", "days": 30},
    "annual": {"label": "Годовой", "days": 365},
}


def register_subscription_handlers(router: Router) -> None:
    @router.message(Command("subscription"))
    @router.message(F.text == "⭐ Подписка")
    async def subscription_handler(message: Message) -> None:
        await _h.show_subscription(message)

    @router.message(Command("referral"))
    async def referral_handler(message: Message) -> None:
        await _h.show_referral(message)

    @router.callback_query(SubscriptionCallback.filter())
    async def subscription_action_handler(query: CallbackQuery, callback_data: SubscriptionCallback) -> None:
        settings = _h.get_settings()
        if query.message is None:
            await query.answer()
            return

        if callback_data.action == "buy":
            plan = callback_data.plan
            if plan not in PLAN_DETAILS:
                await query.answer("Неизвестный тариф", show_alert=True)
                return

            details = PLAN_DETAILS[plan]
            price_map = {
                "basic": settings.stars_price_basic,
                "pro": settings.stars_price_pro,
                "annual": settings.stars_price_annual,
            }
            price = price_map.get(plan, settings.stars_price_basic)

            await query.message.answer_invoice(
                title=f"Подписка «{details['label']}»",
                description=f"AI без лимитов на {details['days']} дней",
                payload=f"sub_{plan}",
                currency="XTR",
                prices=[LabeledPrice(label=f"Подписка {details['label']}", amount=price)],
            )
            await query.answer()

    @router.pre_checkout_query()
    async def pre_checkout_handler(pre_checkout: PreCheckoutQuery) -> None:
        settings = _h.get_settings()
        payload = pre_checkout.invoice_payload
        price_map = {
            "sub_basic": settings.stars_price_basic,
            "sub_pro": settings.stars_price_pro,
            "sub_annual": settings.stars_price_annual,
        }
        expected = price_map.get(payload)
        if expected is None or expected != pre_checkout.total_amount:
            await pre_checkout.answer(ok=False, error_message="Некорректные данные платежа. Попробуй снова.")
            return
        await pre_checkout.answer(ok=True)

    @router.message(F.successful_payment)
    async def successful_payment_handler(message: Message) -> None:
        payment = message.successful_payment
        payload = payment.invoice_payload

        plan_map = {
            "sub_basic": "basic",
            "sub_pro": "pro",
            "sub_annual": "annual",
        }
        plan = plan_map.get(payload)
        if plan is None:
            await message.answer("Оплата получена, но тариф не распознан. Напиши в поддержку.")
            return

        client = _h._get_client()
        result = await client.record_payment(
            telegram_id=message.from_user.id,
            plan=plan,
            amount=payment.total_amount,
            charge_id=payment.telegram_payment_charge_id,
        )

        if not result.get("ok"):
            if result.get("error") == "already_processed":
                await message.answer("Оплата уже обработана. Если доступ не появился — напиши в поддержку.")
                return

        details = PLAN_DETAILS.get(plan, {})
        expires = result.get("expires_at", "—")
        await message.answer(
            payment_success_text(details.get("label", plan), expires),
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
