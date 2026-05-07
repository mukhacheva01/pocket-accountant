from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies import get_services_dep
from shared.clock import utcnow


router = APIRouter(prefix="/events", tags=["events"])


def _serialize_events(events):
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
    return result


class EventActionRequest(BaseModel):
    action: str  # complete | dismiss | snooze


@router.get("/{user_id}/upcoming")
async def upcoming_events(user_id: str, days: int = 7, services=Depends(get_services_dep)):
    events = await services.calendar.upcoming(user_id, days)
    return {"events": _serialize_events(events)}


@router.get("/{user_id}/overdue")
async def overdue_events(user_id: str, services=Depends(get_services_dep)):
    events = await services.calendar.overdue(user_id)
    overdue = [item for item in events if item.due_date < date.today()]
    return {"events": _serialize_events(overdue)}


@router.post("/{user_event_id}/action")
async def event_action(
    user_event_id: str, req: EventActionRequest, services=Depends(get_services_dep),
):
    now = utcnow()
    if req.action == "complete":
        await services.calendar.calendar_repo.mark_completed(user_event_id, now)
    elif req.action == "snooze":
        await services.calendar.calendar_repo.snooze(user_event_id, now + timedelta(days=1))
    elif req.action == "dismiss":
        await services.calendar.calendar_repo.snooze(user_event_id, now + timedelta(days=1))
    return {"user_event_id": user_event_id, "action": req.action, "ok": True}
