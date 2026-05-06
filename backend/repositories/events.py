from datetime import date
from typing import List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.db.enums import EventStatus
from shared.db.models import CalendarEvent, UserEvent


class CalendarEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active_templates(self) -> List[CalendarEvent]:
        result = await self.session.execute(select(CalendarEvent).where(CalendarEvent.active.is_(True)))
        return list(result.scalars().all())

    async def get_user_event(self, user_id: str, calendar_event_id: str, due_date: date) -> UserEvent:
        result = await self.session.execute(
            select(UserEvent).where(
                and_(
                    UserEvent.user_id == user_id,
                    UserEvent.calendar_event_id == calendar_event_id,
                    UserEvent.due_date == due_date,
                )
            )
        )
        return result.scalar_one_or_none()

    async def upsert_user_event(self, user_id: str, template: CalendarEvent, due_date: date) -> UserEvent:
        user_event = await self.get_user_event(user_id, template.id, due_date)
        if user_event is None:
            user_event = UserEvent(
                user_id=user_id,
                calendar_event_id=template.id,
                due_date=due_date,
                status=EventStatus.PENDING,
            )
            self.session.add(user_event)
        else:
            user_event.dismissed = False
        await self.session.flush()
        return user_event

    async def list_upcoming_for_user(self, user_id: str, until: date, include_overdue: bool = False) -> List[UserEvent]:
        filters = [UserEvent.user_id == user_id, UserEvent.dismissed.is_(False)]
        if include_overdue:
            filters.append(UserEvent.status != EventStatus.COMPLETED)
        else:
            filters.append(UserEvent.due_date >= date.today())
        filters.append(UserEvent.due_date <= until)
        result = await self.session.execute(
            select(UserEvent)
            .options(selectinload(UserEvent.calendar_event), selectinload(UserEvent.user))
            .where(*filters)
            .order_by(UserEvent.due_date.asc())
        )
        return list(result.scalars().all())

    async def mark_completed(self, user_event_id: str, completed_at) -> None:
        result = await self.session.execute(select(UserEvent).where(UserEvent.id == user_event_id))
        user_event = result.scalar_one()
        user_event.status = EventStatus.COMPLETED
        user_event.completed_at = completed_at
        await self.session.flush()

    async def snooze(self, user_event_id: str, snoozed_until) -> None:
        result = await self.session.execute(select(UserEvent).where(UserEvent.id == user_event_id))
        user_event = result.scalar_one()
        user_event.snoozed_until = snoozed_until
        await self.session.flush()
