from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List

from shared.clock import utcnow
from shared.db.enums import ReminderStatus, ReminderType
from shared.db.models import Reminder
from backend.repositories.reminders import ReminderRepository
from backend.services.event_policies import build_action_hint, event_matches_reminder_preferences


REMINDER_TYPE_TO_OFFSET = {
    ReminderType.DAYS_7: 7,
    ReminderType.DAYS_3: 3,
    ReminderType.DAYS_1: 1,
    ReminderType.SAME_DAY: 0,
}


@dataclass
class ReminderPlan:
    reminder_type: ReminderType
    scheduled_at: datetime
    action_required: str


class ReminderPlanner:
    @staticmethod
    def build_schedule(due_date: date, offsets: List[int], timezone_name: str) -> List[ReminderPlan]:
        schedule = []
        try:
            tz = ZoneInfo(timezone_name)
        except Exception:
            tz = timezone.utc
        for reminder_type, days_before in REMINDER_TYPE_TO_OFFSET.items():
            if days_before not in offsets:
                continue
            local_dt = datetime.combine(due_date - timedelta(days=days_before), time(hour=9), tzinfo=tz)
            schedule_dt = local_dt.astimezone(timezone.utc)
            schedule.append(
                ReminderPlan(
                    reminder_type=reminder_type,
                    scheduled_at=schedule_dt,
                    action_required="Подготовьте документы и закройте обязательство до дедлайна.",
                )
            )
        overdue_local = datetime.combine(due_date + timedelta(days=1), time(hour=9), tzinfo=tz)
        overdue_at = overdue_local.astimezone(timezone.utc)
        schedule.append(
            ReminderPlan(
                reminder_type=ReminderType.OVERDUE,
                scheduled_at=overdue_at,
                action_required="Проверьте статус подачи и устраните просрочку.",
            )
        )
        return schedule


class ReminderService:
    def __init__(self, reminders: ReminderRepository) -> None:
        self.reminders = reminders

    async def create_reminders_for_event(
        self,
        user_event,
        profile_settings: Dict[str, object],
        timezone_name: str,
    ) -> List[Reminder]:
        calendar_event = getattr(user_event, "calendar_event", None)
        if calendar_event is None:
            return []
        if not event_matches_reminder_preferences(calendar_event.category, profile_settings):
            return []

        offsets = profile_settings.get("offset_days", [3, 1])
        plans = ReminderPlanner.build_schedule(user_event.due_date, offsets, timezone_name)
        reminders = []
        for plan in plans:
            reminders.append(
                Reminder(
                    user_id=user_event.user_id,
                    user_event_id=user_event.id,
                    scheduled_at=plan.scheduled_at,
                    reminder_type=plan.reminder_type,
                    status=ReminderStatus.PENDING,
                    delivery_payload={
                        "action_required": build_action_hint(calendar_event.category),
                        "category": calendar_event.category.value,
                    },
                )
            )
        await self.reminders.schedule_many(reminders)
        return reminders

    async def due_reminders(self, limit: int):
        return await self.reminders.list_due(utcnow(), limit)
