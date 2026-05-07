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
    user_id: str, req: AIQuestionRequest, services=Depends(get_services_dep),
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


class AIQuestionWithHistoryRequest(BaseModel):
    question: str


@router.post("/{user_id}/ask")
async def ask_with_history(
    user_id: str, req: AIQuestionWithHistoryRequest, services=Depends(get_services_dep),
):
    settings = get_settings()
    from backend.services.rate_limit import allow_ai_request

    if not await allow_ai_request(settings, user_id):
        return {"error": "rate_limit", "message": "Слишком много запросов, подожди минуту"}

    from shared.db.session import SessionFactory
    from backend.services.container import build_services

    async with SessionFactory() as session:
        svcs = build_services(session)
        await svcs.onboarding.ensure_user(
            telegram_id=0, username=None, first_name=None, timezone="Europe/Moscow",
        )
        profile = await svcs.onboarding.load_profile(user_id)
        profile_data = {}
        if profile:
            profile_data = {
                "entity_type": profile.entity_type.value if profile.entity_type else None,
                "tax_regime": profile.tax_regime.value if profile.tax_regime else None,
                "has_employees": profile.has_employees,
                "region": profile.region,
            }

        from sqlalchemy import select, desc
        from shared.db.models import AIDialog
        result = await session.execute(
            select(AIDialog)
            .where(AIDialog.user_id == user_id)
            .order_by(desc(AIDialog.created_at))
            .limit(5)
        )
        dialogs = list(reversed(result.scalars().all()))
        history = []
        for d in dialogs:
            history.append({"role": "user", "content": d.question})
            history.append({"role": "assistant", "content": d.answer})

        response = await svcs.ai.answer_tax_question(req.question, profile_data, history)

        session.add(AIDialog(
            user_id=user_id, question=req.question,
            answer=response.text, sources=response.sources,
        ))

        from backend.repositories.users import UserRepository
        user_repo = UserRepository(session)
        real_user = await user_repo.get_by_id(user_id)
        if real_user:
            await svcs.subscription.increment_ai_usage(real_user)

        await session.commit()

    return {
        "answer": response.text,
        "sources": response.sources,
        "confidence": response.confidence,
    }


@router.delete("/{user_id}/history")
async def clear_history(user_id: str):
    from sqlalchemy import delete
    from shared.db.models import AIDialog
    from shared.db.session import SessionFactory

    async with SessionFactory() as session:
        await session.execute(delete(AIDialog).where(AIDialog.user_id == user_id))
        await session.commit()
    return {"ok": True}
