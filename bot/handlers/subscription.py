"""Subscription and payment handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from bot.callbacks import SubscriptionCallback
from bot.handlers._helpers import show_referral, show_subscription
from bot.keyboards import main_menu_keyboard
from bot.messages import payment_success_text
from shared.config import get_settings
from shared.db.enums import SubscriptionPlan
from shared.db.session import SessionFactory
from backend.services.container import build_services
from backend.services.subscription import PLAN_DETAILS


def make_router() -> Router:
    router = Router()

    @router.message(Command("subscription"))
    @router.message(F.text == "⭐ Подписка")
    async def subscription_handler(message: Message) -> None:
        await show_subscription(message)

    @router.message(Command("referral"))
    async def referral_handler(message: Message) -> None:
        await show_referral(message)

    @router.callback_query(SubscriptionCallback.filter())
    async def subscription_action_handler(query: CallbackQuery, callback_data: SubscriptionCallback) -> None:
        settings = get_settings()
        if query.message is None:
            await query.answer()
            return

        if callback_data.action == "buy":
            plan_map = {
                "basic": SubscriptionPlan.BASIC,
                "pro": SubscriptionPlan.PRO,
                "annual": SubscriptionPlan.ANNUAL,
            }
            plan = plan_map.get(callback_data.plan)
            if plan is None:
                await query.answer("Неизвестный тариф", show_alert=True)
                return

            details = PLAN_DETAILS[plan]
            price = settings.stars_price_basic
            if plan == SubscriptionPlan.PRO:
                price = settings.stars_price_pro
            elif plan == SubscriptionPlan.ANNUAL:
                price = settings.stars_price_annual

            await query.message.answer_invoice(
                title=f"Подписка «{details['label']}»",
                description=f"AI без лимитов на {details['days']} дней",
                payload=f"sub_{callback_data.plan}",
                currency="XTR",
                prices=[LabeledPrice(label=f"Подписка {details['label']}", amount=price)],
            )
            await query.answer()

    @router.pre_checkout_query()
    async def pre_checkout_handler(pre_checkout: PreCheckoutQuery) -> None:
        settings = get_settings()
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
            "sub_basic": SubscriptionPlan.BASIC,
            "sub_pro": SubscriptionPlan.PRO,
            "sub_annual": SubscriptionPlan.ANNUAL,
        }
        plan = plan_map.get(payload)
        if plan is None:
            await message.answer("Оплата получена, но тариф не распознан. Напиши в поддержку.")
            return

        async with SessionFactory() as session:
            services = build_services(session)
            user = await services.onboarding.ensure_user(
                telegram_id=message.from_user.id, username=message.from_user.username,
                first_name=message.from_user.first_name, timezone="Europe/Moscow",
            )
            if await services.subscription.payment_exists(payment.telegram_payment_charge_id):
                await message.answer("Оплата уже обработана. Если доступ не появился — напиши в поддержку.")
                return
            sub = await services.subscription.activate(str(user.id), plan)
            await services.subscription.record_payment(
                str(user.id), plan, payment.total_amount,
                payment.telegram_payment_charge_id,
            )
            await session.commit()

        details = PLAN_DETAILS[plan]
        expires = sub.expires_at.strftime("%d.%m.%Y") if sub.expires_at else "—"
        await message.answer(
            payment_success_text(details["label"], expires),
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )

    return router
