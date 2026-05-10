"""AI consultation handlers — FSM chatting, topic shortcuts, clear history."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import bot.handlers.helpers as _h
from bot.keyboards import (
    ai_consult_keyboard,
    ai_consult_reply_keyboard,
    subscription_keyboard,
)
from bot.messages import (
    ai_consult_welcome_text,
    paywall_text,
)
from bot.states import AIConsultStates

logger = logging.getLogger(__name__)


async def show_ai_consult(message: Message, state: FSMContext, actor=None, *, edit: bool = False) -> None:
    actor = actor or message.from_user
    client = _h._get_client()
    data = await client.get_subscription_status(actor.id)

    is_active = data.get("is_active", False)
    can_use = data.get("can_ai", True)
    remaining = data.get("remaining_ai", 0)

    if not can_use:
        prices = data.get("prices", {})
        await _h.respond(message, paywall_text(0), reply_markup=subscription_keyboard(prices), edit=edit)
        return

    await state.set_state(AIConsultStates.chatting)
    text = ai_consult_welcome_text(remaining, is_active)
    if edit:
        await _h.respond(message, text, reply_markup=ai_consult_keyboard(), edit=True)
    else:
        await message.answer(text, reply_markup=ai_consult_reply_keyboard(), parse_mode="Markdown")
        await message.answer("Выбери тему или напиши свой вопрос:", reply_markup=ai_consult_keyboard(), parse_mode="Markdown")


async def do_ai_answer(message: Message, question: str) -> None:
    client = _h._get_client()
    data = await client.get_subscription_status(message.from_user.id)

    if not data.get("can_ai", True):
        prices = data.get("prices", {})
        await message.answer(paywall_text(0), reply_markup=subscription_keyboard(prices), parse_mode="Markdown")
        return

    await message.bot.send_chat_action(message.chat.id, "typing")

    result = await client.ai_full_question(message.from_user.id, question)

    if not result.get("ok"):
        error = result.get("error", "")
        if error == "paywall":
            prices = data.get("prices", {})
            await message.answer(paywall_text(0), reply_markup=subscription_keyboard(prices), parse_mode="Markdown")
            return
        if error == "rate_limit":
            await message.answer("⚠️ Слишком много запросов. Подожди минуту и повтори.", parse_mode="Markdown")
            return

    answer_text = result.get("answer", "")
    is_active = result.get("subscription_active", False)
    footer = ""
    if not is_active:
        new_remaining = result.get("remaining_ai", 0)
        if new_remaining <= 2:
            footer = f"\n\n💬 Осталось запросов: *{new_remaining}*"

    await message.answer(answer_text + footer, reply_markup=ai_consult_keyboard(), parse_mode="Markdown")


def register_ai_consult_handlers(router: Router) -> None:
    @router.message(Command("consult"))
    @router.message(F.text == "💬 AI Консультация")
    async def ai_consult_handler(message: Message, state: FSMContext) -> None:
        await show_ai_consult(message, state)

    @router.message(AIConsultStates.chatting, F.text)
    async def ai_chatting_handler(message: Message, state: FSMContext) -> None:
        if message.text in _h.MAIN_MENU_BUTTONS:
            await state.clear()
            return
        if message.text == "🗑 Новый диалог":
            client = _h._get_client()
            await client.ai_clear_history(message.from_user.id)
            await message.answer("🗑 История очищена!\n\nЗадай новый вопрос 👇", reply_markup=ai_consult_reply_keyboard(), parse_mode="Markdown")
            return
        await do_ai_answer(message, message.text)
