from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.dependencies import get_services_dep


router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.get("/{user_id}/status")
async def subscription_status(user_id: str, services = Depends(get_services_dep)):
    sub = await services.subscription.get_subscription(user_id)
    from shared.db.session import SessionFactory
    from backend.services.container import build_services

    async with SessionFactory() as session:
        svcs = build_services(session)
        from backend.repositories.users import UserRepository
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)
        if user is None:
            return {"error": "user_not_found"}
        can_ai, remaining = await svcs.subscription.can_use_ai(user, sub)

    return {
        "is_active": services.subscription.is_active(sub),
        "plan": sub.plan.value if sub else None,
        "expires_at": sub.expires_at.isoformat() if sub and sub.expires_at else None,
        "can_ai": can_ai,
        "remaining_ai_requests": remaining,
    }


@router.post("/{user_id}/activate")
async def activate_subscription(
    user_id: str, plan: str = "basic", services = Depends(get_services_dep),
):
    from shared.db.enums import SubscriptionPlan
    plan_enum = SubscriptionPlan(plan)
    sub = await services.subscription.activate(user_id, plan_enum)
    return {
        "user_id": user_id,
        "plan": sub.plan.value,
        "is_active": True,
    }
