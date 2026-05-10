"""Event / calendar handlers — upcoming, overdue, documents, laws, reminders."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import bot.handlers.helpers as _h
from bot.callbacks import EventActionCallback
from bot.keyboards import section_shortcuts_keyboard


def register_events_handlers(router: Router) -> None:
    @router.message(Command("events"))
    @router.message(F.text == "📅 События")
    async def events_handler(message: Message) -> None:
        await _h.show_events(message)

    @router.message(Command("calendar"))
    async def calendar_handler(message: Message) -> None:
        await _h.show_calendar(message)

    @router.message(Command("overdue"))
    async def overdue_handler(message: Message) -> None:
        await _h.show_overdue(message)

    @router.message(Command("documents"))
    @router.message(F.text == "📋 Что подать")
    async def documents_handler(message: Message) -> None:
        await _h.show_documents(message)

    @router.message(Command("reminders"))
    async def reminders_handler(message: Message) -> None:
        await _h.show_reminders(message)

    @router.message(Command("laws"))
    async def laws_handler(message: Message) -> None:
        await _h.show_laws(message)

    @router.callback_query(EventActionCallback.filter())
    async def event_action_handler(query: CallbackQuery, callback_data: EventActionCallback) -> None:
        if query.message is None:
            await query.answer()
            return
        client = _h._get_client()
        if callback_data.action == "snooze":
            await client.event_snooze(callback_data.event_id)
            await query.message.edit_text("⏰ Отложено на 1 день.", reply_markup=section_shortcuts_keyboard())
        else:
            await client.event_complete(callback_data.event_id)
            await query.message.edit_text("✅ Выполнено!", reply_markup=section_shortcuts_keyboard())
        await query.answer()
