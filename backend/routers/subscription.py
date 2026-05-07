from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

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
    user_id: str, plan: str = "basic", services=Depends(get_services_dep),
):
    from shared.db.enums import SubscriptionPlan
    plan_enum = SubscriptionPlan(plan)
    sub = await services.subscription.activate(user_id, plan_enum)
    return {
        "user_id": user_id,
        "plan": sub.plan.value,
        "is_active": True,
    }


@router.post("/{user_id}/cancel")
async def cancel_subscription(user_id: str, services=Depends(get_services_dep)):
    from shared.db.session import SessionFactory
    from backend.services.container import build_services

    async with SessionFactory() as session:
        svcs = build_services(session)
        await svcs.subscription.cancel(user_id)
        await session.commit()
    return {"ok": True}


class RecordPaymentRequest(BaseModel):
    plan: str
    stars: int
    telegram_payment_id: str


@router.post("/{user_id}/record-payment")
async def record_payment(user_id: str, req: RecordPaymentRequest, services=Depends(get_services_dep)):
    from shared.db.enums import SubscriptionPlan
    from shared.db.session import SessionFactory
    from backend.services.container import build_services

    plan_enum = SubscriptionPlan(req.plan)
    async with SessionFactory() as session:
        svcs = build_services(session)
        exists = await svcs.subscription.payment_exists(req.telegram_payment_id)
        if exists:
            return {"ok": False, "reason": "already_processed"}
        sub = await svcs.subscription.activate(user_id, plan_enum)
        await svcs.subscription.record_payment(user_id, plan_enum, req.stars, req.telegram_payment_id)
        await session.commit()
    return {
        "ok": True,
        "plan": sub.plan.value,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
    }
