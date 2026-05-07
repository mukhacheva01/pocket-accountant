from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies import get_services_dep


router = APIRouter(prefix="/users", tags=["users"])


class EnsureUserRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    timezone: str = "Europe/Moscow"


class TouchRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    event_type: str = "message"
    payload: Dict[str, Any] = {}


class SetReferralRequest(BaseModel):
    referrer_telegram_id: str
    user_telegram_id: int


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
    user_id: str, req: OnboardingRequest, services=Depends(get_services_dep),
):
    from backend.services.onboarding import OnboardingDraft
    from shared.db.enums import EntityType, TaxRegime

    draft = OnboardingDraft(
        entity_type=EntityType(req.entity_type),
        tax_regime=TaxRegime(req.tax_regime),
        has_employees=req.has_employees,
        marketplaces_enabled=False,
        industry=None,
        region=req.region,
        timezone="Europe/Moscow",
        reminder_settings={
            "notify_taxes": True,
            "notify_reporting": True,
            "notify_documents": True,
            "notify_laws": True,
            "offset_days": [3, 1],
        },
    )
    await services.onboarding.save_profile(user_id, draft)
    return {"user_id": user_id, "entity_type": draft.entity_type.value}


class OnboardingFullRequest(BaseModel):
    entity_type: str
    tax_regime: str
    has_employees: bool = False
    region: str = "Москва"
    planning_entity: bool = False


@router.post("/{user_id}/onboarding-full")
async def complete_onboarding_full(
    user_id: str, req: OnboardingFullRequest, services=Depends(get_services_dep),
):
    from backend.services.onboarding import OnboardingDraft
    from backend.services.profile_matching import ProfileContext
    from shared.db.enums import EntityType, TaxRegime
    from shared.db.session import SessionFactory

    entity_type = EntityType(req.entity_type)
    tax_regime = TaxRegime(req.tax_regime)

    draft = OnboardingDraft(
        entity_type=entity_type,
        tax_regime=tax_regime,
        has_employees=req.has_employees,
        marketplaces_enabled=False,
        industry=None,
        region=req.region,
        timezone="Europe/Moscow",
        reminder_settings={
            "notify_taxes": True,
            "notify_reporting": True,
            "notify_documents": True,
            "notify_laws": True,
            "offset_days": [3, 1],
            "planning_entity": req.planning_entity,
        },
    )

    async with SessionFactory() as session:
        from backend.services.container import build_services
        svcs = build_services(session)
        await svcs.onboarding.save_profile(user_id, draft)

        profile_context = ProfileContext(
            entity_type=entity_type,
            tax_regime=tax_regime,
            has_employees=req.has_employees,
            marketplaces_enabled=False,
            region=req.region,
            industry=None,
            reminder_offsets=[3, 1],
        )
        await svcs.calendar.sync_user_events(user_id, profile_context)
        user_events = await svcs.calendar.upcoming(user_id, 370)
        for ue in user_events:
            await svcs.reminders.create_reminders_for_event(
                ue, draft.reminder_settings, draft.timezone,
            )
        await session.commit()

    return {"user_id": user_id, "entity_type": entity_type.value, "ok": True}


@router.post("/touch")
async def touch_user(req: TouchRequest):
    from shared.clock import utcnow
    from shared.db.models import UserActivity
    from shared.db.session import SessionFactory
    from backend.services.container import build_services

    async with SessionFactory() as session:
        svcs = build_services(session)
        user = await svcs.onboarding.ensure_user(
            telegram_id=req.telegram_id,
            username=req.username,
            first_name=req.first_name,
            timezone="Europe/Moscow",
        )
        profile = await svcs.onboarding.load_profile(str(user.id))
        sub = await svcs.subscription.get_subscription(str(user.id))

        now = utcnow()
        user.last_seen_at = now
        if not user.is_active:
            user.is_active = True
            user.reactivated_at = now

        session.add(UserActivity(
            user_id=user.id, event_type=req.event_type, payload=req.payload,
        ))
        await session.commit()

        is_active = svcs.subscription.is_active(sub)
        can_ai, remaining = await svcs.subscription.can_use_ai(user, sub)

    profile_data = None
    if profile is not None:
        profile_data = {
            "entity_type": profile.entity_type.value if profile.entity_type else None,
            "tax_regime": profile.tax_regime.value if profile.tax_regime else None,
            "has_employees": profile.has_employees,
            "marketplaces_enabled": profile.marketplaces_enabled,
            "region": profile.region,
            "reminder_settings": profile.reminder_settings or {},
        }

    return {
        "user_id": str(user.id),
        "telegram_id": user.telegram_id,
        "profile": profile_data,
        "subscription": {
            "is_active": is_active,
            "plan": sub.plan.value if sub else None,
            "expires_at": sub.expires_at.isoformat() if sub and sub.expires_at else None,
            "can_ai": can_ai,
            "remaining_ai_requests": remaining,
        },
    }


@router.post("/{user_id}/set-referral")
async def set_referral(user_id: str, req: SetReferralRequest):
    from sqlalchemy import select
    from shared.db.models import User
    from shared.db.session import SessionFactory

    async with SessionFactory() as session:
        from backend.services.container import build_services
        svcs = build_services(session)
        user = await svcs.onboarding.ensure_user(
            telegram_id=req.user_telegram_id,
            username=None,
            first_name=None,
            timezone="Europe/Moscow",
        )
        if user.referred_by is not None or str(req.user_telegram_id) == req.referrer_telegram_id:
            return {"ok": False, "reason": "already_referred_or_self"}

        user.referred_by = req.referrer_telegram_id
        result = await session.execute(
            select(User).where(User.telegram_id == int(req.referrer_telegram_id))
        )
        referrer = result.scalar_one_or_none()
        if referrer:
            referrer.referral_bonus_requests += 3
        await session.commit()

    return {"ok": True}


@router.get("/{user_id}/referral-info")
async def referral_info(user_id: str, telegram_id: int):
    from sqlalchemy import select, func
    from shared.db.models import User
    from shared.db.session import SessionFactory
    from backend.services.container import build_services

    async with SessionFactory() as session:
        svcs = build_services(session)
        user = await svcs.onboarding.ensure_user(
            telegram_id=telegram_id,
            username=None,
            first_name=None,
            timezone="Europe/Moscow",
        )
        result = await session.execute(
            select(func.count()).select_from(User).where(User.referred_by == str(telegram_id))
        )
        ref_count = result.scalar() or 0

    return {
        "referral_count": ref_count,
        "bonus_requests": user.referral_bonus_requests,
    }
