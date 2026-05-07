"""AI consultation handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers._helpers import (
    MAIN_MENU_BUTTONS,
    do_ai_answer,
    show_ai_consult,
    show_home,
)
from bot.keyboards import ai_consult_reply_keyboard
from bot.states import AIConsultStates
from shared.db.session import SessionFactory
from backend.services.container import build_services


router = Router()


@router.message(Command("consult"))
@router.message(F.text == "💬 AI Консультация")
async def ai_consult_handler(message: Message, state: FSMContext) -> None:
    await show_ai_consult(message, state)


@router.message(F.text == "🗑 Новый диалог")
async def clear_ai_history_handler(message: Message, state: FSMContext) -> None:
    async with SessionFactory() as session:
        services = build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        from sqlalchemy import delete
        from shared.db.models import AIDialog
        await session.execute(delete(AIDialog).where(AIDialog.user_id == user.id))
        await session.commit()
    await state.set_state(AIConsultStates.chatting)
    await message.answer("🗑 История очищена. Начинаем с чистого листа!\n\nЗадай вопрос 👇", reply_markup=ai_consult_reply_keyboard(), parse_mode="Markdown")


@router.message(AIConsultStates.chatting)
async def ai_consult_chatting_handler(message: Message, state: FSMContext) -> None:
    raw_text = (message.text or "").strip()
    if not raw_text:
        return
    if raw_text == "🏠 Главная":
        await state.clear()
        await show_home(message)
        return
    if raw_text in MAIN_MENU_BUTTONS and raw_text not in {"💬 AI Консультация", "🗑 Новый диалог"}:
        await state.clear()
        return
    if raw_text == "💬 AI Консультация":
        await show_ai_consult(message, state)
        return
    await do_ai_answer(message, raw_text)
