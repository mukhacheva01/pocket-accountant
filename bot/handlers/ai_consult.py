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
    settings = _h.get_settings()
    actor = actor or message.from_user
    async with _h.SessionFactory() as session:
        services = _h.build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=actor.id, username=actor.username,
            first_name=actor.first_name, timezone="Europe/Moscow",
        )
        sub = await services.subscription.get_subscription(str(user.id))
        is_active = services.subscription.is_active(sub)
        can_use, remaining = await services.subscription.can_use_ai(user, sub)

    if not can_use:
        prices = {
            "basic": settings.stars_price_basic,
            "pro": settings.stars_price_pro,
            "annual": settings.stars_price_annual,
        }
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
    settings = _h.get_settings()
    async with _h.SessionFactory() as session:
        services = _h.build_services(session)
        user = await services.onboarding.ensure_user(
            telegram_id=message.from_user.id, username=message.from_user.username,
            first_name=message.from_user.first_name, timezone="Europe/Moscow",
        )
        sub = await services.subscription.get_subscription(str(user.id))
        can_use, remaining = await services.subscription.can_use_ai(user, sub)

        if not can_use:
            prices = {
                "basic": settings.stars_price_basic,
                "pro": settings.stars_price_pro,
                "annual": settings.stars_price_annual,
            }
            await message.answer(paywall_text(0), reply_markup=subscription_keyboard(prices), parse_mode="Markdown")
            return

        if not await _h.allow_ai_request(settings, str(user.id)):
            await message.answer("⚠️ Слишком много запросов. Подожди минуту и повтори.", parse_mode="Markdown")
            return

        await message.bot.send_chat_action(message.chat.id, "typing")

        profile = await services.onboarding.load_profile(str(user.id))

        from sqlalchemy import select, desc
        from shared.db.models import AIDialog
        result = await session.execute(
            select(AIDialog)
            .where(AIDialog.user_id == user.id)
            .order_by(desc(AIDialog.created_at))
            .limit(5)
        )
        dialogs = list(reversed(result.scalars().all()))
        history = []
        for d in dialogs:
            history.append({"role": "user", "content": d.question})
            history.append({"role": "assistant", "content": d.answer})

        response = await services.ai.answer_tax_question(
            question,
            {
                "entity_type": profile.entity_type.value if profile else None,
                "tax_regime": profile.tax_regime.value if profile else None,
                "has_employees": profile.has_employees if profile else None,
            },
            history=history,
        )

        session.add(AIDialog(user_id=user.id, question=question, answer=response.text, sources=response.sources))
        await services.subscription.increment_ai_usage(user)
        await session.commit()

        is_active = services.subscription.is_active(sub)
        footer = ""
        if not is_active:
            _, new_remaining = await services.subscription.can_use_ai(user, sub)
            if new_remaining <= 2:
                footer = f"\n\n💬 Осталось запросов: *{new_remaining}*"

    await message.answer(response.text + footer, reply_markup=ai_consult_keyboard(), parse_mode="Markdown")


def register_ai_consult_handlers(router: Router) -> None:
    @router.message(Command("consult"))
    @router.message(F.text == "💬 AI Консультация")
    async def ai_consult_handler(message: Message, state: FSMContext) -> None:
        await show_ai_consult(message, state)

    @router.message(AIConsultStates.chatting)
    async def ai_consult_chatting_handler(message: Message, state: FSMContext) -> None:
        raw_text = (message.text or "").strip()
        if not raw_text:
            return
        if raw_text == "🏠 Главная":
            await state.clear()
            await _h.show_home(message)
            return
        if raw_text in _h.MAIN_MENU_BUTTONS and raw_text not in {"💬 AI Консультация", "🗑 Новый диалог"}:
            await state.clear()
            return
        if raw_text == "💬 AI Консультация":
            await show_ai_consult(message, state)
            return
        await do_ai_answer(message, raw_text)

    @router.message(F.text == "🗑 Новый диалог")
    async def clear_ai_history_handler(message: Message, state: FSMContext) -> None:
        async with _h.SessionFactory() as session:
            services = _h.build_services(session)
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
