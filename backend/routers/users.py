from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from backend.dependencies import get_services_dep
from backend.services.onboarding import OnboardingDraft
from backend.services.profile_matching import ProfileContext
from shared.clock import utcnow
from shared.db.enums import EntityType, TaxRegime
from shared.db.models import User, UserActivity


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
    industry: str | None = None
    reminder_settings: dict = {}
    has_profile: bool = False


class OnboardingRequest(BaseModel):
    entity_type: str
    tax_regime: str
    has_employees: bool = False
    region: str = "Москва"


class OnboardingFullRequest(BaseModel):
    entity_type: str
    tax_regime: str
    has_employees: bool = False
    marketplaces_enabled: bool = False
    industry: str | None = None
    region: str = "Москва"
    timezone: str = "Europe/Moscow"
    reminder_settings: dict = {}
    planning_entity: bool = False


class ReferralRequest(BaseModel):
    referrer_telegram_id: str


class ActivityRequest(BaseModel):
    event_type: str
    payload: dict = {}


@router.post("/ensure")
async def ensure_user(req: EnsureUserRequest, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=req.telegram_id,
        username=req.username,
        first_name=req.first_name,
        timezone=req.timezone,
    )
    return {
        "user_id": str(user.id),
        "telegram_id": user.telegram_id,
        "referral_bonus_requests": user.referral_bonus_requests,
        "referred_by": user.referred_by,
    }


@router.get("/{user_id}/profile")
async def get_profile(user_id: str, services=Depends(get_services_dep)):
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
        industry=profile.industry if hasattr(profile, "industry") else None,
        reminder_settings=profile.reminder_settings or {},
        has_profile=True,
    )


@router.post("/{user_id}/onboarding")
async def complete_onboarding(
    user_id: str, req: OnboardingRequest, services=Depends(get_services_dep),
):
    draft = OnboardingDraft(
        entity_type=EntityType(req.entity_type),
        tax_regime=TaxRegime(req.tax_regime),
        has_employees=req.has_employees,
        marketplaces_enabled=False,
        industry=None,
        region=req.region,
        timezone="Europe/Moscow",
        reminder_settings={},
    )
    profile = await services.onboarding.save_profile(user_id, draft)
    return {"user_id": user_id, "entity_type": profile.entity_type.value}


@router.post("/{user_id}/onboarding-full")
async def complete_onboarding_full(
    user_id: str, req: OnboardingFullRequest, services=Depends(get_services_dep),
):
    reminder_settings = req.reminder_settings or {
        "notify_taxes": True,
        "notify_reporting": True,
        "notify_documents": True,
        "notify_laws": True,
        "offset_days": [3, 1],
    }
    if req.planning_entity:
        reminder_settings["planning_entity"] = True

    draft = OnboardingDraft(
        entity_type=EntityType(req.entity_type),
        tax_regime=TaxRegime(req.tax_regime),
        has_employees=req.has_employees,
        marketplaces_enabled=req.marketplaces_enabled,
        industry=req.industry,
        region=req.region,
        timezone=req.timezone,
        reminder_settings=reminder_settings,
    )
    profile = await services.onboarding.save_profile(user_id, draft)

    profile_context = ProfileContext(
        entity_type=draft.entity_type,
        tax_regime=draft.tax_regime,
        has_employees=draft.has_employees,
        marketplaces_enabled=draft.marketplaces_enabled,
        region=draft.region,
        industry=draft.industry,
        reminder_offsets=reminder_settings.get("offset_days", [3, 1]),
    )
    await services.calendar.sync_user_events(user_id, profile_context)
    user_events = await services.calendar.upcoming(user_id, 370)
    for ue in user_events:
        await services.reminders.create_reminders_for_event(ue, reminder_settings, req.timezone)

    return {"user_id": user_id, "entity_type": profile.entity_type.value}


class SaveProfileRequest(BaseModel):
    entity_type: str
    tax_regime: str
    has_employees: bool = False
    marketplaces_enabled: bool = False
    industry: str | None = None
    region: str = "Москва"
    timezone: str = "Europe/Moscow"
    reminder_settings: dict = {}


@router.post("/{user_id}/save-profile")
async def save_profile(
    user_id: str, req: SaveProfileRequest, services=Depends(get_services_dep),
):
    reminder_settings = req.reminder_settings or {
        "notify_taxes": True,
        "notify_reporting": True,
        "notify_documents": True,
        "notify_laws": True,
        "offset_days": [3, 1],
    }

    draft = OnboardingDraft(
        entity_type=EntityType(req.entity_type),
        tax_regime=TaxRegime(req.tax_regime),
        has_employees=req.has_employees,
        marketplaces_enabled=req.marketplaces_enabled,
        industry=req.industry,
        region=req.region,
        timezone=req.timezone,
        reminder_settings=reminder_settings,
    )
    profile = await services.onboarding.save_profile(user_id, draft)

    profile_context = ProfileContext(
        entity_type=draft.entity_type,
        tax_regime=draft.tax_regime,
        has_employees=draft.has_employees,
        marketplaces_enabled=draft.marketplaces_enabled,
        region=draft.region,
        industry=draft.industry,
        reminder_offsets=reminder_settings.get("offset_days", [3, 1]),
    )
    await services.calendar.sync_user_events(user_id, profile_context)
    user_events = await services.calendar.upcoming(user_id, 370)
    for ue in user_events:
        await services.reminders.create_reminders_for_event(ue, reminder_settings, req.timezone)

    return {"user_id": user_id, "entity_type": profile.entity_type.value}


@router.get("/{user_id}/referral-info")
async def referral_info(user_id: str, services=Depends(get_services_dep)):
    session = services.onboarding.users.session
    user = await services.onboarding.users.get_by_id(user_id)
    if user is None:
        return {"error": "user_not_found"}
    result = await session.execute(
        select(func.count()).select_from(User).where(User.referred_by == str(user.telegram_id))
    )
    ref_count = result.scalar() or 0
    return {
        "referral_count": ref_count,
        "bonus_requests": user.referral_bonus_requests,
    }


@router.post("/{user_id}/process-referral")
async def process_referral(
    user_id: str, req: ReferralRequest, services=Depends(get_services_dep),
):
    session = services.onboarding.users.session
    user = await services.onboarding.users.get_by_id(user_id)
    if user is None:
        return {"error": "user_not_found"}
    if user.referred_by is not None:
        return {"ok": False, "reason": "already_referred"}
    if str(user.telegram_id) == req.referrer_telegram_id:
        return {"ok": False, "reason": "self_referral"}

    user.referred_by = req.referrer_telegram_id
    result = await session.execute(
        select(User).where(User.telegram_id == int(req.referrer_telegram_id))
    )
    referrer = result.scalar_one_or_none()
    if referrer:
        referrer.referral_bonus_requests += 3
    return {"ok": True}


@router.post("/{user_id}/activity")
async def record_activity(
    user_id: str, req: ActivityRequest, services=Depends(get_services_dep),
):
    session = services.onboarding.users.session
    user = await services.onboarding.users.get_by_id(user_id)
    if user is None:
        return {"error": "user_not_found"}
    now = utcnow()
    user.last_seen_at = now
    if not user.is_active:
        user.is_active = True
        user.reactivated_at = now
    if req.event_type == "command":
        user.last_command = req.payload.get("command", "")
    session.add(UserActivity(user_id=user.id, event_type=req.event_type, payload=req.payload))
    return {"ok": True}
