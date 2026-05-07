from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.dependencies import get_services_dep
from backend.services.profile_matching import ProfileContext
from shared.config import get_settings


router = APIRouter(prefix="/laws", tags=["laws"])


@router.get("/{user_id}/relevant")
async def relevant_laws(user_id: str, services=Depends(get_services_dep)):
    settings = get_settings()
    profile = await services.onboarding.load_profile(user_id)
    if profile is None:
        return {"updates": []}
    context = ProfileContext(
        entity_type=profile.entity_type,
        tax_regime=profile.tax_regime,
        has_employees=profile.has_employees,
        marketplaces_enabled=profile.marketplaces_enabled,
        region=profile.region,
        industry=profile.industry if hasattr(profile, "industry") else None,
        reminder_offsets=profile.reminder_settings.get("offset_days", [3, 1]) if profile.reminder_settings else [3, 1],
    )
    updates = await services.laws.relevant_updates(context, min_importance=settings.law_min_importance_score)
    result = []
    for item in updates:
        result.append({
            "id": str(item.id),
            "title": item.title,
            "summary": item.summary if hasattr(item, "summary") else "",
            "effective_date": item.effective_date.isoformat() if item.effective_date else None,
            "importance_score": item.importance_score if hasattr(item, "importance_score") else 0,
        })
    return {"updates": result}
