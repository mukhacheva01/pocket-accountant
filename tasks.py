import logging
from datetime import date

from aiogram import Bot
from sqlalchemy import select

from accountant_bot.core.clock import utcnow
from accountant_bot.db.enums import ReminderStatus
from accountant_bot.db.models import User
from accountant_bot.db.session import SessionFactory
from accountant_bot.services.container import build_services
from accountant_bot.services.notifications import NotificationComposer
from accountant_bot.services.profile_matching import build_profile_context


logger = logging.getLogger(__name__)


async def sync_user_events() -> None:
    async with SessionFactory() as session:
        services = build_services(session)
        result = await session.execute(select(User))
        users = list(result.scalars().all())
        for user in users:
            user_id = str(user.id)
            profile = await services.onboarding.load_profile(user_id)
            if profile is None:
                continue
            context = build_profile_context(profile)
            await services.calendar.sync_user_events(user_id, context)
            user_events = await services.calendar.upcoming(user_id, 370)
            for user_event in user_events:
                await services.reminders.create_reminders_for_event(
                    user_event,
                    profile.reminder_settings,
                    user.timezone,
                )
        await session.commit()
        logger.info("user_events_synced", extra={"users": len(users)})


async def sync_ozon_connections(limit: int) -> None:
    async with SessionFactory() as session:
        services = build_services(session)
        results = await services.ozon_sync.sync_all_connections(limit=limit)
        await session.commit()
        logger.info(
            "ozon_connections_synced",
            extra={
                "connections": len(results),
                "synced": sum(1 for item in results if item.status == "synced"),
                "partial": sum(1 for item in results if item.status == "partial"),
                "failed": sum(1 for item in results if item.status == "failed"),
            },
        )


async def send_due_reminders(bot: Bot, batch_size: int) -> None:
    async with SessionFactory() as session:
        services = build_services(session)
        reminders = await services.reminders.due_reminders(limit=batch_size)
        sent = 0
        failed = 0
        for reminder in reminders:
            user_event = reminder.user_event
            calendar_event = reminder.user_event.calendar_event
            payload = NotificationComposer.build_reminder_payload(reminder, user_event, calendar_event)
            text = (
                f"{payload.title}\n"
                f"Срок: {payload.due_date.isoformat()}\n"
                f"{payload.action_required}\n"
                f"{payload.consequence_hint}"
            )
            try:
                await bot.send_message(chat_id=user_event.user.telegram_id, text=text)
            except Exception:
                reminder.status = ReminderStatus.FAILED
                failed += 1
                logger.exception("reminder_delivery_failed", extra={"reminder_id": str(reminder.id)})
                await session.commit()
                continue
            reminder.sent_at = utcnow()
            reminder.status = ReminderStatus.SENT
            sent += 1
            await session.commit()
        logger.info("reminders_sent", extra={"count": sent, "failed": failed})


async def deliver_law_updates(bot: Bot, min_importance: int) -> None:
    async with SessionFactory() as session:
        services = build_services(session)
        result = await session.execute(select(User.id))
        user_ids = [row[0] for row in result.fetchall()]
        sent = 0
        for user_id in user_ids:
            profile = await services.onboarding.load_profile(str(user_id))
            if profile is None:
                continue
            if not profile.reminder_settings.get("notify_laws", True):
                continue
            context = build_profile_context(profile)
            updates = await services.laws.relevant_updates_for_user(str(user_id), context, min_importance)
            for update in updates[:3]:
                try:
                    await bot.send_message(
                        chat_id=profile.user.telegram_id,
                        text=(
                            f"Изменение: {update.title}\n"
                            f"Источник: {update.source}\n"
                            f"Что делать: {update.action_required or 'Проверьте применимость.'}"
                        ),
                    )
                except Exception:
                    logger.exception("law_update_delivery_failed", extra={"law_update_id": str(update.id), "user_id": str(user_id)})
                    continue
                await services.laws.mark_delivered(str(update.id), str(user_id), utcnow())
                sent += 1
                await session.commit()
        logger.info("law_updates_delivered", extra={"count": sent, "date": date.today().isoformat()})
