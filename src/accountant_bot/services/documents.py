from typing import List

from accountant_bot.services.calendar import CalendarService
from accountant_bot.services.event_policies import build_action_hint, build_consequence_hint, is_document_related


class DocumentsService:
    def __init__(self, calendar: CalendarService) -> None:
        self.calendar = calendar

    async def upcoming_documents(self, user_id: str) -> List[dict]:
        events = await self.calendar.upcoming(user_id, days=30)
        documents = []
        for item in events:
            if item.calendar_event is None or not is_document_related(item.calendar_event.category):
                continue
            documents.append(
                {
                    "title": item.calendar_event.title,
                    "due_date": item.due_date.isoformat(),
                    "status": item.status.value,
                    "priority": item.calendar_event.priority,
                    "legal_basis": item.calendar_event.legal_basis,
                    "action_required": build_action_hint(item.calendar_event.category),
                    "risk_hint": build_consequence_hint(item.calendar_event.category),
                }
            )
        return documents
