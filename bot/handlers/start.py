"""/start, /menu, welcome — entry point handlers."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import bot.handlers.helpers as _h
from bot.keyboards import onboarding_entity_type_keyboard
from bot.states import OnboardingStates


def register_start_handlers(router: Router) -> None:
    @router.message(CommandStart())
    async def start_handler(message: Message, state: FSMContext) -> None:
        args = message.text.split(maxsplit=1)
        ref_id = None
        if len(args) > 1 and args[1].startswith("ref_"):
            ref_id = args[1][4:]

        data = await _h.load_profile(message.from_user)

        if ref_id:
            client = _h._get_client()
            await client.save_referral(message.from_user.id, ref_id)

        if data.get("has_profile"):
            await state.clear()
            await _h.show_home(message)
            return
        await state.set_state(OnboardingStates.entity_type)
        await message.answer(_h.welcome_text(message.from_user.first_name), reply_markup=onboarding_entity_type_keyboard(), parse_mode="Markdown")

    @router.message(Command("menu"))
    @router.message(F.text == "🏠 Главная")
    async def menu_handler(message: Message) -> None:
        await _h.show_home(message)

    @router.message(F.text == "Отмена")
    async def cancel_handler(message: Message, state: FSMContext) -> None:
        await state.clear()
        await _h.show_home(message)
