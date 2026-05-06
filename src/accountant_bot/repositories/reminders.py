from datetime import datetime
from typing import Iterable, List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from accountant_bot.db.enums import ReminderStatus
from accountant_bot.db.models import Reminder, UserEvent


class ReminderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def schedule_many(self, reminders: Iterable[Reminder]) -> None:
        for reminder in reminders:
            result = await self.session.execute(
                select(Reminder).where(
                    and_(
                        Reminder.user_event_id == reminder.user_event_id,
                        Reminder.reminder_type == reminder.reminder_type,
                    )
                )
            )
            existing = result.scalar_one_or_none()
            if existing is None:
                self.session.add(reminder)
                continue
            existing.scheduled_at = reminder.scheduled_at
            existing.delivery_payload = reminder.delivery_payload
            if existing.status != ReminderStatus.SENT:
                existing.status = ReminderStatus.PENDING
                existing.sent_at = None
        await self.session.flush()

    async def list_due(self, now: datetime, limit: int) -> List[Reminder]:
        result = await self.session.execute(
            select(Reminder)
            .options(
                selectinload(Reminder.user_event).selectinload(UserEvent.calendar_event),
                selectinload(Reminder.user_event).selectinload(UserEvent.user),
            )
            .where(
                and_(
                    Reminder.status == ReminderStatus.PENDING,
                    Reminder.sent_at.is_(None),
                    Reminder.scheduled_at <= now,
                )
            )
            .order_by(Reminder.scheduled_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
