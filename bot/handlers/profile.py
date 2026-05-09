"""Profile and settings handlers."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

import bot.handlers.helpers as _h


def register_profile_handlers(router: Router) -> None:
    @router.message(Command("profile"))
    @router.message(F.text == "👤 Профиль")
    async def profile_handler(message: Message) -> None:
        await _h.show_profile(message)

    @router.message(Command("settings"))
    async def settings_handler(message: Message) -> None:
        await _h.show_settings(message)
