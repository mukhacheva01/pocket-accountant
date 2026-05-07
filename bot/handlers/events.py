"""Events, calendar, documents, reminders, and laws handlers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.types import User as TelegramUser

from bot.backend_client import BackendClient
from bot.callbacks import EventActionCallback
from bot.handlers._helpers import respond
from bot.keyboards import (
    documents_shortcuts_keyboard,
    event_actions_keyboard,
    laws_shortcuts_keyboard,
    onboarding_entity_type_keyboard,
    reminders_shortcuts_keyboard,
    section_shortcuts_keyboard,
)
from bot.messages import welcome_text


async def show_events(
    message: Message, client: BackendClient,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    actor = actor or message.from_user
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    user_id = user_data["user_id"]
    events_data = await client.upcoming_events(user_id, 14)
    events = events_data.get("events", [])
    if not events:
        await respond(message, "📅 На ближайшие 14 дней событий нет.", reply_markup=section_shortcuts_keyboard(), edit=edit)
        return
    lines = ["📅 *Ближайшие события:*\n"]
    for item in events[:5]:
        title = item.get("title", "Событие")
        lines.append(f"• *{title}* — до {item.get('due_date', '')}")
    await respond(message, "\n".join(lines), reply_markup=event_actions_keyboard(str(events[0].get("id", ""))), edit=edit)


async def show_calendar(
    message: Message, client: BackendClient,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    actor = actor or message.from_user
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    events_data = await client.upcoming_events(user_data["user_id"], 30)
    events = events_data.get("events", [])
    if not events:
        await respond(message, "📅 На ближайшие 30 дней событий нет.", reply_markup=section_shortcuts_keyboard(), edit=edit)
        return
    lines = ["📅 *Календарь на 30 дней:*\n"]
    for item in events[:10]:
        title = item.get("title", "Событие")
        lines.append(f"{item.get('due_date', '')} — {title}")
    await respond(message, "\n".join(lines), reply_markup=section_shortcuts_keyboard(), edit=edit)


async def show_overdue(
    message: Message, client: BackendClient,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    actor = actor or message.from_user
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    data = await client.overdue_events(user_data["user_id"])
    overdue = data.get("events", [])
    if not overdue:
        await respond(message, "✅ Просроченных событий нет!", reply_markup=section_shortcuts_keyboard(), edit=edit)
        return
    lines = ["🔴 *Просроченные события:*\n"]
    for item in overdue[:10]:
        title = item.get("title", "Событие")
        lines.append(f"• *{title}* — до {item.get('due_date', '')}")
    await respond(message, "\n".join(lines), reply_markup=section_shortcuts_keyboard(), edit=edit)


async def show_documents(
    message: Message, client: BackendClient,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    actor = actor or message.from_user
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    data = await client.upcoming_documents(user_data["user_id"])
    documents = data.get("documents", [])
    if not documents:
        await respond(message, "📋 Обязательных подач в ближайшие 30 дней нет.", reply_markup=documents_shortcuts_keyboard(), edit=edit)
        return
    lines = ["📋 *Что нужно подать:*\n"]
    for item in documents[:5]:
        lines.append(f"• *{item['title']}* до {item['due_date']}\n  {item['action_required']}")
    await respond(message, "\n".join(lines), reply_markup=documents_shortcuts_keyboard(), edit=edit)


async def show_reminders(
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
    s = profile.get("reminder_settings") or {}
    offsets = s.get("offset_days", [3, 1])
    text = (
        "🔔 *Напоминания*\n\n"
        f"Интервалы: *{', '.join(str(i) for i in offsets)}* дней\n"
        f"Налоги: {'✅' if s.get('notify_taxes', True) else '❌'}\n"
        f"Отчётность: {'✅' if s.get('notify_reporting', True) else '❌'}\n"
        f"Документы: {'✅' if s.get('notify_documents', True) else '❌'}\n"
        f"Законы: {'✅' if s.get('notify_laws', True) else '❌'}"
    )
    await respond(message, text, reply_markup=reminders_shortcuts_keyboard(), edit=edit)


async def show_laws(
    message: Message, client: BackendClient,
    actor: TelegramUser | None = None, *, edit: bool = False,
) -> None:
    actor = actor or message.from_user
    user_data = await client.ensure_user(
        telegram_id=actor.id, username=actor.username,
        first_name=actor.first_name, timezone="Europe/Moscow",
    )
    user_id = user_data["user_id"]
    profile_data = await client.get_profile(user_id)
    profile = profile_data.get("profile")
    if profile is None:
        await respond(message, welcome_text(actor.first_name), reply_markup=onboarding_entity_type_keyboard(), edit=edit)
        return
    data = await client.law_updates(user_id)
    updates = data.get("updates", [])
    if not updates:
        await respond(message, "📰 Новых обновлений для твоего профиля нет.", reply_markup=laws_shortcuts_keyboard(), edit=edit)
        return
    lines = ["📰 *Новости законов:*\n"]
    for item in updates[:5]:
        effective = item.get("effective_date", "дата не указана")
        lines.append(f"• *{item.get('title', '')}*\n  Вступает: {effective}")
    await respond(message, "\n".join(lines), reply_markup=laws_shortcuts_keyboard(), edit=edit)


def register(parent_router: Router, client: BackendClient) -> None:
    @parent_router.message(Command("events"))
    @parent_router.message(F.text == "📅 События")
    async def events_handler(message: Message) -> None:
        await show_events(message, client)

    @parent_router.message(Command("calendar"))
    async def calendar_handler(message: Message) -> None:
        await show_calendar(message, client)

    @parent_router.message(Command("overdue"))
    async def overdue_handler(message: Message) -> None:
        await show_overdue(message, client)

    @parent_router.message(Command("documents"))
    @parent_router.message(F.text == "📋 Что подать")
    async def documents_handler(message: Message) -> None:
        await show_documents(message, client)

    @parent_router.message(Command("reminders"))
    async def reminders_handler(message: Message) -> None:
        await show_reminders(message, client)

    @parent_router.message(Command("laws"))
    async def laws_handler(message: Message) -> None:
        await show_laws(message, client)

    @parent_router.callback_query(EventActionCallback.filter())
    async def event_action_handler(query: CallbackQuery, callback_data: EventActionCallback) -> None:
        if query.message is None:
            await query.answer()
            return
        await client.event_action(callback_data.event_id, callback_data.action)
        if callback_data.action == "snooze":
            await query.message.edit_text("⏰ Отложено на 1 день.", reply_markup=section_shortcuts_keyboard())
        else:
            await query.message.edit_text("✅ Выполнено!", reply_markup=section_shortcuts_keyboard())
        await query.answer()
