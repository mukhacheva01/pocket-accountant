"""Profile, settings, and referral handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.handlers._helpers import show_profile


def make_router() -> Router:
    router = Router()

    @router.message(Command("profile"))
    @router.message(F.text == "👤 Профиль")
    async def profile_handler(message: Message) -> None:
        await show_profile(message)

    return router
