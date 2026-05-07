from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.dependencies import get_services_dep
from backend.services.profile_matching import ProfileContext


router = APIRouter(prefix="/laws", tags=["laws"])


@router.get("/{user_id}/updates")
async def relevant_updates(user_id: str, min_importance: int = 70, services=Depends(get_services_dep)):
    profile = await services.onboarding.load_profile(user_id)
    if profile is None:
        return {"updates": []}
    context = ProfileContext(
        entity_type=profile.entity_type,
        tax_regime=profile.tax_regime,
        has_employees=profile.has_employees,
        marketplaces_enabled=profile.marketplaces_enabled,
        region=profile.region,
        industry=profile.industry,
        reminder_offsets=profile.reminder_settings.get("offset_days", [3, 1]),
    )
    updates = await services.laws.relevant_updates(context, min_importance)
    return {
        "updates": [
            {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary,
                "effective_date": item.effective_date.isoformat() if item.effective_date else None,
                "importance_score": item.importance_score,
                "action_required": item.action_required,
            }
            for item in updates
        ]
    }
