"""Subscription and payment handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from aiogram.types import User as TelegramUser

from bot.backend_client import BackendClient
from bot.callbacks import SubscriptionCallback
from bot.handlers._helpers import PLAN_DETAILS, respond
from bot.keyboards import (
    main_menu_keyboard,
    section_shortcuts_keyboard,
    subscription_keyboard,
    subscription_manage_keyboard,
)
from bot.messages import payment_success_text, paywall_text, referral_text, subscription_status_text
from shared.config import get_settings


async def show_subscription(
    message: Message, client: BackendClient,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    settings = get_settings()
    actor = actor or message.from_user
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    user_id = user_data["user_id"]
    sub_data = await client.subscription_status(user_id)
    is_active = sub_data.get("is_active", False)

    if is_active:
        plan_label = PLAN_DETAILS.get(sub_data.get("plan", ""), {}).get("label", "Активна")
        expires = sub_data.get("expires_at", "—")
        text = subscription_status_text(plan_label, expires, True)
        await respond(message, text, reply_markup=subscription_manage_keyboard(), edit=edit)
    else:
        prices = {
            "basic": settings.stars_price_basic,
            "pro": settings.stars_price_pro,
            "annual": settings.stars_price_annual,
        }
        remaining = sub_data.get("remaining_ai_requests", 0)
        text = paywall_text(remaining)
        await respond(message, text, reply_markup=subscription_keyboard(prices), edit=edit)


async def show_referral(
    message: Message, client: BackendClient,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    actor = actor or message.from_user
    bot_info = await message.bot.me()
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    ref_data = await client.get_referral_info(user_data["user_id"], actor.id)
    ref_count = ref_data.get("referral_count", 0)
    bonus = ref_data.get("bonus_requests", 0)
    text = referral_text(bot_info.username, actor.id, ref_count, bonus)
    await respond(message, text, reply_markup=section_shortcuts_keyboard(), edit=edit)


def register(parent_router: Router, client: BackendClient) -> None:
    settings = get_settings()

    @parent_router.message(Command("subscription"))
    @parent_router.message(F.text == "⭐ Подписка")
    async def subscription_handler(message: Message) -> None:
        await show_subscription(message, client)

    @parent_router.message(Command("referral"))
    async def referral_handler(message: Message) -> None:
        await show_referral(message, client)

    @parent_router.callback_query(SubscriptionCallback.filter())
    async def subscription_action_handler(query: CallbackQuery, callback_data: SubscriptionCallback) -> None:
        if query.message is None:
            await query.answer()
            return

        if callback_data.action == "buy":
            plan = callback_data.plan
            details = PLAN_DETAILS.get(plan)
            if details is None:
                await query.answer("Неизвестный тариф", show_alert=True)
                return

            price = settings.stars_price_basic
            if plan == "pro":
                price = settings.stars_price_pro
            elif plan == "annual":
                price = settings.stars_price_annual

            await query.message.answer_invoice(
                title=f"Подписка «{details['label']}»",
                description=f"AI без лимитов на {details['days']} дней",
                payload=f"sub_{plan}",
                currency="XTR",
                prices=[LabeledPrice(label=f"Подписка {details['label']}", amount=price)],
            )
            await query.answer()

    @parent_router.pre_checkout_query()
    async def pre_checkout_handler(pre_checkout: PreCheckoutQuery) -> None:
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

    @parent_router.message(F.successful_payment)
    async def successful_payment_handler(message: Message) -> None:
        payment = message.successful_payment
        payload = payment.invoice_payload

        plan_key_map = {
            "sub_basic": "basic",
            "sub_pro": "pro",
            "sub_annual": "annual",
        }
        plan = plan_key_map.get(payload)
        if plan is None:
            await message.answer("Оплата получена, но тариф не распознан. Напиши в поддержку.")
            return

        user_data = await client.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        user_id = user_data["user_id"]

        await client.record_payment(
            user_id, plan, payment.total_amount,
            payment.telegram_payment_charge_id,
        )
        sub_data = await client.activate_subscription(user_id, plan)

        details = PLAN_DETAILS.get(plan, {})
        expires = sub_data.get("expires_at", "—")
        await message.answer(
            payment_success_text(details.get("label", plan), expires),
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown",
        )
