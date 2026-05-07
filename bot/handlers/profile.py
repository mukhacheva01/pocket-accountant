"""Profile and settings handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types import User as TelegramUser

from bot.backend_client import BackendClient
from bot.handlers._helpers import entity_label, planned_entity_label, respond, tax_regime_label
from bot.keyboards import (
    onboarding_entity_type_keyboard,
    profile_shortcuts_keyboard,
    settings_shortcuts_keyboard,
)
from bot.messages import welcome_text


async def show_profile(
    message: Message, client: BackendClient,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    actor = actor or message.from_user
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    profile_data = await client.get_profile(user_data["user_id"])
    profile = profile_data.get("profile")
    if profile is None:
        await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
        return
    planned = planned_entity_label(profile)
    text = (
        f"👤 *Профиль бизнеса*\n\n"
        f"Тип: *{planned or entity_label(profile.get('entity_type', ''))}*\n"
        f"Режим: *{tax_regime_label(profile.get('tax_regime', ''))}*\n"
        f"Сотрудники: {'да' if profile.get('has_employees') else 'нет'}\n"
        f"Маркетплейсы: {'да' if profile.get('marketplaces_enabled') else 'нет'}\n"
        f"Регион: {profile.get('region', '')}"
    )
    await respond(message, text, reply_markup=profile_shortcuts_keyboard(), edit=edit)


async def show_settings(message: Message, *, edit: bool = False) -> None:
    await respond(
        message,
        "⚙️ *Настройки*\n\nОбнови профиль или измени напоминания 👇",
        reply_markup=settings_shortcuts_keyboard(),
        edit=edit,
    )


def register(parent_router: Router, client: BackendClient) -> None:
    @parent_router.message(Command("profile"))
    @parent_router.message(F.text == "👤 Профиль")
    async def profile_handler(message: Message) -> None:
        await show_profile(message, client)

    @parent_router.message(Command("settings"))
    async def settings_handler(message: Message) -> None:
        await show_settings(message)
