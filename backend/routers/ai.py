from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, desc, select

from backend.dependencies import get_services_dep
from backend.services.rate_limit import allow_ai_request
from shared.config import get_settings
from shared.db.models import AIDialog

router = APIRouter(prefix="/ai", tags=["ai"])


class AIQuestionRequest(BaseModel):
    question: str
    history: list = []


@router.post("/{user_id}/question")
async def ask_question(
    user_id: str, req: AIQuestionRequest, services=Depends(get_services_dep),
):
    settings = get_settings()
    if not await allow_ai_request(settings, user_id):
        return {"error": "rate_limit", "message": "Слишком много запросов, подожди минуту"}

    profile = await services.onboarding.load_profile(user_id)
    profile_data = {}
    if profile:
        profile_data = {
            "entity_type": profile.entity_type.value if profile.entity_type else None,
            "tax_regime": profile.tax_regime.value if profile.tax_regime else None,
            "has_employees": profile.has_employees,
            "region": profile.region,
        }

    response = await services.ai.answer_tax_question(req.question, profile_data, req.history)

    user = await services.onboarding.users.get_by_id(user_id)
    if user is not None:
        sub = await services.subscription.get_subscription(user_id)
        await services.subscription.increment_ai_usage(user)

    return {
        "answer": response.text,
        "sources": response.sources,
        "confidence": response.confidence,
    }


@router.delete("/{user_id}/history")
async def clear_history(user_id: str, services=Depends(get_services_dep)):
    session = services.onboarding.users.session
    await session.execute(delete(AIDialog).where(AIDialog.user_id == user_id))
    return {"ok": True}


@router.get("/{user_id}/history")
async def get_history(user_id: str, limit: int = 5, services=Depends(get_services_dep)):
    session = services.onboarding.users.session
    result = await session.execute(
        select(AIDialog)
        .where(AIDialog.user_id == user_id)
        .order_by(desc(AIDialog.created_at))
        .limit(limit)
    )
    dialogs = list(reversed(result.scalars().all()))
    history = []
    for d in dialogs:
        history.append({"role": "user", "content": d.question})
        history.append({"role": "assistant", "content": d.answer})
    return {"history": history}
