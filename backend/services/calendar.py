from datetime import date, timedelta
from typing import List

from backend.repositories.events import CalendarEventRepository
from backend.services.profile_matching import ProfileContext, template_matches_profile


class CalendarService:
    def __init__(self, calendar_repo: CalendarEventRepository) -> None:
        self.calendar_repo = calendar_repo

    async def sync_user_events(self, user_id: str, profile: ProfileContext) -> int:
        created = 0
        templates = await self.calendar_repo.list_active_templates()
        for template in templates:
            if not template_matches_profile(template, profile):
                continue
            await self.calendar_repo.upsert_user_event(user_id, template, template.due_date)
            created += 1
        return created

    async def upcoming(self, user_id: str, days: int = 30):
        return await self.calendar_repo.list_upcoming_for_user(user_id, date.today() + timedelta(days=days))

    async def overdue(self, user_id: str):
        return await self.calendar_repo.list_upcoming_for_user(user_id, date.today(), include_overdue=True)

