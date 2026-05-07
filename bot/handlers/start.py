"""Start command and home screen handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import User as TelegramUser

from bot.backend_client import BackendClient
from bot.handlers._helpers import (
    entity_label,
    format_money,
    planned_entity_label,
    respond,
    tax_regime_label,
)
from bot.keyboards import (
    main_menu_keyboard,
    onboarding_entity_type_keyboard,
    section_shortcuts_keyboard,
)
from bot.messages import welcome_text
from bot.states import OnboardingStates


router = Router()


async def show_home(
    message: Message, client: BackendClient,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    actor = actor or message.from_user
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    user_id = user_data["user_id"]
    profile_data = await client.get_profile(user_id)
    profile = profile_data.get("profile")

    if profile is None:
        await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
        return

    events_data = await client.upcoming_events(user_id, 7)
    events = events_data.get("events", [])
    balance_data = await client.get_balance(user_id)
    sub_data = await client.subscription_status(user_id)
    next_event = events[0] if events else None
    planned = planned_entity_label(profile)

    lines = [
        "🏠 *Главная*",
        f"👤 {planned or entity_label(profile.get('entity_type', ''))} | {tax_regime_label(profile.get('tax_regime', ''))}",
        f"💰 Баланс: *{format_money(balance_data.get('balance', '0'))}* ₽",
        f"📈 Доходы: {format_money(balance_data.get('income', '0'))} ₽ | 📉 Расходы: {format_money(balance_data.get('expense', '0'))} ₽",
    ]
    if next_event is not None:
        lines.append(f"📅 Ближайшее: *{next_event.get('title', 'Событие')}* до {next_event.get('due_date', '')}")
    else:
        lines.append("📅 Ближайших дедлайнов нет")

    if not sub_data.get("is_active"):
        lines.append(f"💬 AI-запросов сегодня: *{sub_data.get('remaining_ai_requests', 0)}*")

    await respond(
        message, "\n".join(lines),
        reply_markup=section_shortcuts_keyboard() if edit else main_menu_keyboard(),
        edit=edit,
    )


def register(parent_router: Router, client: BackendClient) -> None:
    @parent_router.message(CommandStart())
    async def start_handler(message: Message, state: FSMContext) -> None:
        args = message.text.split(maxsplit=1)
        ref_id = None
        if len(args) > 1 and args[1].startswith("ref_"):
            ref_id = args[1][4:]

        user_data = await client.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        user_id = user_data["user_id"]
        profile_data = await client.get_profile(user_id)
        profile = profile_data.get("profile")

        if ref_id:
            await client.set_referral(ref_id, message.from_user.id)

        if profile is not None:
            await state.clear()
            await show_home(message, client)
            return
        await state.set_state(OnboardingStates.entity_type)
        await message.answer(welcome_text(message.from_user.first_name), reply_markup=onboarding_entity_type_keyboard(), parse_mode="Markdown")

    @parent_router.message(Command("menu"))
    @parent_router.message(F.text == "🏠 Главная")
    async def menu_handler(message: Message) -> None:
        await show_home(message, client)

    @parent_router.message(F.text == "Отмена")
    async def cancel_handler(message: Message, state: FSMContext) -> None:
        await state.clear()
        await show_home(message, client)
