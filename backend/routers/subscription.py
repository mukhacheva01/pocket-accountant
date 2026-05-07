from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies import get_services_dep
from shared.db.enums import SubscriptionPlan


router = APIRouter(prefix="/subscription", tags=["subscription"])


class PaymentRequest(BaseModel):
    plan: str
    stars: int
    telegram_payment_id: str


class ProcessPaymentRequest(BaseModel):
    plan: str
    amount: int
    charge_id: str


@router.get("/{user_id}/status")
async def subscription_status(user_id: str, services=Depends(get_services_dep)):
    sub = await services.subscription.get_subscription(user_id)
    user = await services.onboarding.users.get_by_id(user_id)
    if user is None:
        return {"error": "user_not_found"}
    can_ai, remaining = await services.subscription.can_use_ai(user, sub)
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
    plan_enum = SubscriptionPlan(plan)
    sub = await services.subscription.activate(user_id, plan_enum)
    return {
        "user_id": user_id,
        "plan": sub.plan.value,
        "is_active": True,
    }


@router.post("/{user_id}/cancel")
async def cancel_subscription(user_id: str, services=Depends(get_services_dep)):
    sub = await services.subscription.cancel(user_id)
    return {"user_id": user_id, "plan": sub.plan.value, "ok": True}


@router.post("/{user_id}/payment")
async def record_payment(
    user_id: str, req: PaymentRequest, services=Depends(get_services_dep),
):
    plan_enum = SubscriptionPlan(req.plan)
    if await services.subscription.payment_exists(req.telegram_payment_id):
        return {"error": "duplicate", "message": "Payment already processed"}
    sub = await services.subscription.activate(user_id, plan_enum)
    await services.subscription.record_payment(
        user_id, plan_enum, req.stars, req.telegram_payment_id,
    )
    return {
        "user_id": user_id,
        "plan": sub.plan.value,
        "is_active": True,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
    }


@router.post("/{user_id}/process-payment")
async def process_payment(
    user_id: str, req: ProcessPaymentRequest, services=Depends(get_services_dep),
):
    plan_enum = SubscriptionPlan(req.plan)
    if await services.subscription.payment_exists(req.charge_id):
        return {"already_processed": True}
    sub = await services.subscription.activate(user_id, plan_enum)
    await services.subscription.record_payment(
        user_id, plan_enum, req.amount, req.charge_id,
    )
    return {
        "user_id": user_id,
        "plan": sub.plan.value,
        "is_active": True,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        "already_processed": False,
    }
