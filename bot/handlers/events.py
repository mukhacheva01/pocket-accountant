"""Event and calendar handlers."""

from __future__ import annotations

from datetime import timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.callbacks import EventActionCallback, PageCallback
from bot.handlers._helpers import (
    show_calendar,
    show_documents,
    show_events,
    show_laws,
    show_overdue,
    show_reminders,
    utcnow,
)
from bot.keyboards import section_shortcuts_keyboard
from shared.db.session import SessionFactory
from backend.services.container import build_services


def make_router() -> Router:
    router = Router()

    @router.message(Command("events"))
    @router.message(F.text == "📅 События")
    async def events_handler(message: Message) -> None:
        await show_events(message)

    @router.message(Command("calendar"))
    async def calendar_handler(message: Message) -> None:
        await show_calendar(message)

    @router.message(Command("overdue"))
    async def overdue_handler(message: Message) -> None:
        await show_overdue(message)

    @router.message(Command("documents"))
    @router.message(F.text == "📋 Что подать")
    async def documents_handler(message: Message) -> None:
        await show_documents(message)

    @router.message(Command("reminders"))
    async def reminders_handler(message: Message) -> None:
        await show_reminders(message)

    @router.message(Command("laws"))
    async def laws_handler(message: Message) -> None:
        await show_laws(message)

    @router.callback_query(EventActionCallback.filter())
    async def event_action_handler(query: CallbackQuery, callback_data: EventActionCallback) -> None:
        if query.message is None:
            await query.answer()
            return
        async with SessionFactory() as session:
            services = build_services(session)
            if callback_data.action == "snooze":
                await services.calendar.calendar_repo.snooze(callback_data.event_id, utcnow() + timedelta(days=1))
                await query.message.edit_text("⏰ Отложено на 1 день.", reply_markup=section_shortcuts_keyboard())
            else:
                await services.calendar.calendar_repo.mark_completed(callback_data.event_id, utcnow())
                await query.message.edit_text("✅ Выполнено!", reply_markup=section_shortcuts_keyboard())
            await session.commit()
        await query.answer()

    @router.callback_query(PageCallback.filter())
    async def page_handler(query: CallbackQuery, callback_data: PageCallback) -> None:
        await query.answer("Скоро будет!", show_alert=False)

    return router
