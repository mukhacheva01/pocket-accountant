"""Help handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.handlers._helpers import show_help


def make_router() -> Router:
    router = Router()

    @router.message(Command("help"))
    @router.message(F.text == "❓ Помощь")
    async def help_handler(message: Message) -> None:
        await show_help(message)

    return router
