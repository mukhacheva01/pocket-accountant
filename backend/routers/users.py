from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies import get_services_dep


router = APIRouter(prefix="/users", tags=["users"])


class EnsureUserRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    timezone: str = "Europe/Moscow"


class ProfileResponse(BaseModel):
    user_id: str
    entity_type: str | None = None
    tax_regime: str | None = None
    has_employees: bool = False
    marketplaces_enabled: bool = False
    region: str | None = None
    reminder_settings: dict = {}
    has_profile: bool = False


class OnboardingRequest(BaseModel):
    entity_type: str
    tax_regime: str
    has_employees: bool = False
    region: str = "Москва"


@router.post("/ensure")
async def ensure_user(req: EnsureUserRequest, services = Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=req.telegram_id,
        username=req.username,
        first_name=req.first_name,
        timezone=req.timezone,
    )
    return {"user_id": str(user.id), "telegram_id": user.telegram_id}


@router.get("/{user_id}/profile")
async def get_profile(user_id: str, services = Depends(get_services_dep)):
    profile = await services.onboarding.load_profile(user_id)
    if profile is None:
        return ProfileResponse(user_id=user_id, has_profile=False)
    return ProfileResponse(
        user_id=user_id,
        entity_type=profile.entity_type.value if profile.entity_type else None,
        tax_regime=profile.tax_regime.value if profile.tax_regime else None,
        has_employees=profile.has_employees,
        marketplaces_enabled=profile.marketplaces_enabled,
        region=profile.region,
        reminder_settings=profile.reminder_settings or {},
        has_profile=True,
    )


@router.post("/{user_id}/onboarding")
async def complete_onboarding(
    user_id: str, req: OnboardingRequest, services = Depends(get_services_dep),
):
    from backend.services.onboarding import OnboardingDraft

    draft = OnboardingDraft(
        entity_type=req.entity_type,
        tax_regime=req.tax_regime,
        has_employees=req.has_employees,
        region=req.region,
    )
    profile = await services.onboarding.complete_onboarding(user_id, draft)
    return {"user_id": user_id, "entity_type": profile.entity_type.value}
