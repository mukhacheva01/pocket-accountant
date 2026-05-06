from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies import get_services_dep

from shared.config import get_settings

router = APIRouter(prefix="/ai", tags=["ai"])


class AIQuestionRequest(BaseModel):
    question: str
    history: list = []


@router.post("/{user_id}/question")
async def ask_question(
    user_id: str, req: AIQuestionRequest, services = Depends(get_services_dep),
):
    settings = get_settings()
    from backend.services.rate_limit import allow_ai_request

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
    return {
        "answer": response.text,
        "sources": response.sources,
        "confidence": response.confidence,
    }
