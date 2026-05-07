"""Start command and main menu handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers._helpers import (
    load_profile,
    show_home,
    show_settings,
)
from bot.keyboards import onboarding_entity_type_keyboard
from bot.messages import welcome_text
from bot.states import OnboardingStates
from shared.db.session import SessionFactory
from backend.services.container import build_services


def make_router() -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start_handler(message: Message, state: FSMContext) -> None:
        args = message.text.split(maxsplit=1)
        ref_id = None
        if len(args) > 1 and args[1].startswith("ref_"):
            ref_id = args[1][4:]

        _, profile = await load_profile(message.from_user)

        if ref_id:
            async with SessionFactory() as session:
                services = build_services(session)
                user = await services.onboarding.ensure_user(
                    telegram_id=message.from_user.id, username=message.from_user.username,
                    first_name=message.from_user.first_name, timezone="Europe/Moscow",
                )
                if user.referred_by is None and str(message.from_user.id) != ref_id:
                    user.referred_by = ref_id
                    from sqlalchemy import select
                    from shared.db.models import User
                    result = await session.execute(select(User).where(User.telegram_id == int(ref_id)))
                    referrer = result.scalar_one_or_none()
                    if referrer:
                        referrer.referral_bonus_requests += 3
                    await session.commit()

        if profile is not None:
            await state.clear()
            await show_home(message)
            return
        await state.set_state(OnboardingStates.entity_type)
        await message.answer(welcome_text(message.from_user.first_name), reply_markup=onboarding_entity_type_keyboard(), parse_mode="Markdown")

    @router.message(Command("menu"))
    @router.message(F.text == "🏠 Главная")
    async def menu_handler(message: Message) -> None:
        await show_home(message)

    @router.message(F.text == "Отмена")
    async def cancel_handler(message: Message, state: FSMContext) -> None:
        await state.clear()
        await show_home(message)

    @router.message(Command("settings"))
    async def settings_handler(message: Message) -> None:
        await show_settings(message)

    return router
