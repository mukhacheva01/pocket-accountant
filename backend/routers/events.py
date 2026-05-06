from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies import get_services_dep


router = APIRouter(prefix="/events", tags=["events"])


class EventActionRequest(BaseModel):
    action: str  # complete | dismiss | snooze


@router.get("/{user_id}/upcoming")
async def upcoming_events(user_id: str, days: int = 7, services = Depends(get_services_dep)):
    events = await services.calendar.upcoming(user_id, days)
    result = []
    for ue in events:
        ce = ue.calendar_event
        result.append({
            "user_event_id": str(ue.id),
            "title": ce.title if ce else "",
            "description": ce.description if ce else "",
            "category": ce.category.value if ce else "",
            "due_date": ue.due_date.isoformat(),
            "status": ue.status.value,
        })
    return {"events": result}


@router.post("/{user_event_id}/action")
async def event_action(
    user_event_id: str, req: EventActionRequest, services = Depends(get_services_dep),
):
    from shared.db.session import SessionFactory
    from shared.db.models import UserEvent
    from shared.db.enums import EventStatus
    from sqlalchemy import select

    async with SessionFactory() as session:
        stmt = select(UserEvent).where(UserEvent.id == user_event_id)
        result = await session.execute(stmt)
        ue = result.scalar_one_or_none()
        if ue is None:
            return {"error": "not_found"}

        if req.action == "complete":
            ue.status = EventStatus.COMPLETED
            from shared.clock import utcnow
            ue.completed_at = utcnow()
        elif req.action == "dismiss":
            ue.dismissed = True
        elif req.action == "snooze":
            from datetime import timedelta
            from shared.clock import utcnow
            ue.snoozed_until = utcnow() + timedelta(days=1)

        await session.commit()
        return {"user_event_id": user_event_id, "action": req.action, "ok": True}
