"""/help handler."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

import bot.handlers.helpers as _h


def register_help_handlers(router: Router) -> None:
    @router.message(Command("help"))
    @router.message(F.text == "❓ Помощь")
    async def help_handler(message: Message) -> None:
        await _h.show_help(message)
