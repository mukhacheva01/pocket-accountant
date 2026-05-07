"""AI consultation handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.types import User as TelegramUser

from bot.backend_client import BackendClient
from bot.handlers._helpers import MAIN_MENU_BUTTONS, respond
from bot.keyboards import (
    ai_consult_keyboard,
    ai_consult_reply_keyboard,
    main_menu_keyboard,
    subscription_keyboard,
)
from bot.messages import ai_consult_welcome_text, paywall_text
from bot.states import AIConsultStates
from shared.config import get_settings


async def show_ai_consult(
    message: Message, client: BackendClient, state: FSMContext,
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
    remaining = sub_data.get("remaining_ai_requests", 0)
    can_use = sub_data.get("can_use_ai", remaining > 0 or is_active)

    if not can_use:
        prices = {
            "basic": settings.stars_price_basic,
            "pro": settings.stars_price_pro,
            "annual": settings.stars_price_annual,
        }
        await respond(message, paywall_text(0), reply_markup=subscription_keyboard(prices), edit=edit)
        return

    await state.set_state(AIConsultStates.chatting)
    text = ai_consult_welcome_text(remaining, is_active)
    if edit:
        await respond(message, text, reply_markup=ai_consult_keyboard(), edit=True)
    else:
        await message.answer(text, reply_markup=ai_consult_reply_keyboard(), parse_mode="Markdown")
        await message.answer("Выбери тему или напиши свой вопрос:", reply_markup=ai_consult_keyboard(), parse_mode="Markdown")


async def do_ai_answer(message: Message, client: BackendClient, question: str) -> None:
    settings = get_settings()
    user_data = await client.ensure_user(
        telegram_id=message.from_user.id, username=message.from_user.username,
        first_name=message.from_user.first_name, timezone="Europe/Moscow",
    )
    user_id = user_data["user_id"]
    sub_data = await client.subscription_status(user_id)
    is_active = sub_data.get("is_active", False)
    remaining = sub_data.get("remaining_ai_requests", 0)
    can_use = sub_data.get("can_use_ai", remaining > 0 or is_active)

    if not can_use:
        prices = {
            "basic": settings.stars_price_basic,
            "pro": settings.stars_price_pro,
            "annual": settings.stars_price_annual,
        }
        await message.answer(paywall_text(0), reply_markup=subscription_keyboard(prices), parse_mode="Markdown")
        return

    await message.bot.send_chat_action(message.chat.id, "typing")

    result = await client.ask_ai_with_history(user_id, question)
    answer_text = result.get("answer", "Не удалось получить ответ.")

    footer = ""
    if not is_active:
        new_remaining = result.get("remaining_ai_requests", remaining - 1)
        if new_remaining <= 2:
            footer = f"\n\n💬 Осталось запросов: *{new_remaining}*"

    await message.answer(answer_text + footer, reply_markup=ai_consult_keyboard(), parse_mode="Markdown")


def register(parent_router: Router, client: BackendClient) -> None:
    @parent_router.message(Command("consult"))
    @parent_router.message(F.text == "💬 AI Консультация")
    async def ai_consult_handler(message: Message, state: FSMContext) -> None:
        await show_ai_consult(message, client, state)

    @parent_router.message(F.text == "🗑 Новый диалог")
    async def clear_ai_history_handler(message: Message, state: FSMContext) -> None:
        user_data = await client.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        await client.clear_ai_history(user_data["user_id"])
        await state.set_state(AIConsultStates.chatting)
        await message.answer("🗑 История очищена. Начинаем с чистого листа!\n\nЗадай вопрос 👇", reply_markup=ai_consult_reply_keyboard(), parse_mode="Markdown")

    @parent_router.message(AIConsultStates.chatting)
    async def ai_consult_chatting_handler(message: Message, state: FSMContext) -> None:
        raw_text = (message.text or "").strip()
        if not raw_text:
            return
        if raw_text == "🏠 Главная":
            await state.clear()
            from bot.handlers.start import show_home
            await show_home(message, client)
            return
        if raw_text in MAIN_MENU_BUTTONS and raw_text not in {"💬 AI Консультация", "🗑 Новый диалог"}:
            await state.clear()
            return
        if raw_text == "💬 AI Консультация":
            await show_ai_consult(message, client, state)
            return
        await do_ai_answer(message, client, raw_text)

    @parent_router.message(Command("calc"))
    async def calc_handler(message: Message) -> None:
        payload = message.text.partition(" ")[2].strip()
        if not payload:
            await message.answer("Пришли запрос так: /calc усн 6 доход 500000", parse_mode="Markdown")
            return
        await client.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        result = await client.parse_tax_query(payload)
        if result.get("error"):
            await message.answer("Не понял режим или сумму.\nПример: /calc самозанятый доход 120к от физлиц", parse_mode="Markdown")
            return
        text = result.get("rendered", result.get("text", "Результат расчёта"))
        await message.answer(text, reply_markup=main_menu_keyboard())
