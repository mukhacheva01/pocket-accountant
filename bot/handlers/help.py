"""Help handler."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.backend_client import BackendClient
from bot.handlers._helpers import respond
from bot.keyboards import help_shortcuts_keyboard
from bot.messages import help_text


async def show_help(message: Message, *, edit: bool = False) -> None:
    await respond(message, help_text(), reply_markup=help_shortcuts_keyboard(), edit=edit)


def register(parent_router: Router, client: BackendClient) -> None:
    @parent_router.message(Command("help"))
    @parent_router.message(F.text == "❓ Помощь")
    async def help_handler(message: Message) -> None:
        await show_help(message)
