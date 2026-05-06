import logging
from datetime import date

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from sqlalchemy import select

from shared.clock import utcnow
from shared.db.enums import ReminderStatus
from shared.db.models import User
from shared.db.session import SessionFactory
from backend.services.container import build_services
from backend.services.notifications import NotificationComposer
from backend.services.profile_matching import ProfileContext


logger = logging.getLogger(__name__)


async def sync_user_events() -> None:
    async with SessionFactory() as session:
        services = build_services(session)
        result = await session.execute(select(User))
        users = list(result.scalars().all())
        for user in users:
            user_id = str(user.id)
            try:
                profile = await services.onboarding.load_profile(str(user_id))
                if profile is None:
                    continue
                context = ProfileContext(
                    entity_type=profile.entity_type,
                    tax_regime=profile.tax_regime,
                    has_employees=profile.has_employees,
                    marketplaces_enabled=profile.marketplaces_enabled,
                    region=profile.region,
                    industry=profile.industry,
                    reminder_offsets=profile.reminder_settings.get("offset_days", [3, 1]),
                )
                await services.calendar.sync_user_events(str(user_id), context)
                user_events = await services.calendar.upcoming(str(user_id), 370)
                for user_event in user_events:
                    await services.reminders.create_reminders_for_event(
                        user_event,
                        profile.reminder_settings,
                        user.timezone,
                    )
            except Exception:
                logger.exception("sync_user_events_error", extra={"user_id": str(user_id)})
        await session.commit()
        logger.info("user_events_synced", extra={"users": len(users)})


async def send_due_reminders(bot: Bot, batch_size: int) -> None:
    async with SessionFactory() as session:
        services = build_services(session)
        reminders = await services.reminders.due_reminders(limit=batch_size)
        sent = 0
        for reminder in reminders:
            try:
                user_event = reminder.user_event
                calendar_event = reminder.user_event.calendar_event
                payload = NotificationComposer.build_reminder_payload(reminder, user_event, calendar_event)
                text = (
                    f"🔔 *{payload.title}*\n"
                    f"📅 Срок: {payload.due_date.isoformat()}\n"
                    f"📋 {payload.action_required}\n"
                    f"⚠️ {payload.consequence_hint}"
                )
                await bot.send_message(chat_id=user_event.user.telegram_id, text=text, parse_mode="Markdown")
                reminder.sent_at = utcnow()
                reminder.status = ReminderStatus.SENT
                sent += 1
            except TelegramForbiddenError:
                logger.warning("user_blocked_bot", extra={"user_id": str(reminder.user_id)})
                reminder.status = ReminderStatus.FAILED
                # Mark user inactive
                result = await session.execute(select(User).where(User.id == reminder.user_id))
                user = result.scalar_one_or_none()
                if user:
                    user.is_active = False
                    user.deactivated_at = utcnow()
            except Exception:
                logger.exception("reminder_send_error", extra={"reminder_id": str(reminder.id)})
                reminder.status = ReminderStatus.FAILED
        await session.commit()
        logger.info("reminders_sent", extra={"count": sent})


async def deliver_law_updates(bot: Bot, min_importance: int) -> None:
    async with SessionFactory() as session:
        services = build_services(session)
        result = await session.execute(select(User.id).where(User.is_active.is_(True)))
        user_ids = [row[0] for row in result.fetchall()]
        sent = 0
        for user_id in user_ids:
            try:
                profile = await services.onboarding.load_profile(str(user_id))
                if profile is None:
                    continue
                context = ProfileContext(
                    entity_type=profile.entity_type,
                    tax_regime=profile.tax_regime,
                    has_employees=profile.has_employees,
                    marketplaces_enabled=profile.marketplaces_enabled,
                    region=profile.region,
                    industry=profile.industry,
                    reminder_offsets=profile.reminder_settings.get("offset_days", [3, 1]),
                )
                updates = await services.laws.relevant_updates(context, min_importance)
                for update in updates[:3]:
                    if await services.laws.was_delivered(str(update.id), str(user_id)):
                        continue
                    await bot.send_message(
                        chat_id=profile.user.telegram_id,
                        text=(
                            f"📰 *{update.title}*\n"
                            f"Источник: {update.source}\n"
                            f"Что делать: {update.action_required or 'Проверь применимость.'}"
                        ),
                        parse_mode="Markdown",
                    )
                    await services.laws.mark_delivered(str(update.id), str(user_id), utcnow(), "sent")
                    sent += 1
            except TelegramForbiddenError:
                logger.warning("user_blocked_bot_law", extra={"user_id": str(user_id)})
            except Exception:
                logger.exception("law_delivery_error", extra={"user_id": str(user_id)})
        await session.commit()
        logger.info("law_updates_delivered", extra={"count": sent, "date": date.today().isoformat()})
