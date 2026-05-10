"""Aggregated API endpoints consumed by the bot service via httpx.

This router provides all data the bot needs without requiring bot
to access the DB or import backend services directly.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.dependencies import get_services_dep
from shared.clock import utcnow
from shared.config import get_settings

router = APIRouter(prefix="/bot", tags=["bot-gateway"])


# ── Request / Response schemas ──────────────────────────────────


class TrackActivityRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    event_type: str = "message"
    payload: dict = {}
    command: str | None = None


class OnboardingWithSyncRequest(BaseModel):
    entity_type: str
    tax_regime: str
    has_employees: bool = False
    region: str = "Москва"
    timezone: str = "Europe/Moscow"
    reminder_settings: dict = {}
    marketplaces_enabled: bool = False
    industry: str | None = None


class AddFromTextRequest(BaseModel):
    source_text: str
    record_kind: str  # income | expense


class SaveDialogRequest(BaseModel):
    question: str
    answer: str
    sources: list = []


class RecordPaymentRequest(BaseModel):
    plan: str
    amount: int
    charge_id: str


class ReferralRequest(BaseModel):
    referrer_telegram_id: str


class CompareRegimesRequest(BaseModel):
    activity: str
    monthly_income: str
    has_employees: bool = False
    counterparties: str = "mixed"
    region: str = "Москва"


class MatchTemplateRequest(BaseModel):
    text: str


# ── Endpoints ───────────────────────────────────────────────────


@router.post("/users/track-activity")
async def track_activity(req: TrackActivityRequest, services=Depends(get_services_dep)):
    await services.onboarding.ensure_user(
        telegram_id=req.telegram_id,
        username=req.username,
        first_name=req.first_name,
        timezone="Europe/Moscow",
    )
    from shared.db.session import SessionFactory
    from shared.db.models import UserActivity

    async with SessionFactory() as session:
        from backend.services.container import build_services

        svcs = build_services(session)
        from backend.repositories.users import UserRepository

        user_repo = UserRepository(session)
        db_user = await user_repo.get_by_telegram_id(req.telegram_id)
        if db_user is None:
            return {"ok": False}

        now = utcnow()
        db_user.last_seen_at = now
        if not db_user.is_active:
            db_user.is_active = True
            db_user.reactivated_at = now
        if req.command:
            db_user.last_command = req.command

        session.add(
            UserActivity(user_id=db_user.id, event_type=req.event_type, payload=req.payload)
        )
        await session.commit()

        profile = await svcs.onboarding.load_profile(str(db_user.id))
        sub = await svcs.subscription.get_subscription(str(db_user.id))

    return {
        "ok": True,
        "user_id": str(db_user.id),
        "has_profile": profile is not None,
        "profile": _serialize_profile(profile) if profile else None,
        "subscription": _serialize_subscription(services, sub, db_user),
    }


@router.get("/users/{telegram_id}/home")
async def user_home(telegram_id: int, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    user_id = str(user.id)
    profile = await services.onboarding.load_profile(user_id)
    if profile is None:
        return {"has_profile": False, "user_id": user_id}

    events = await services.calendar.upcoming(user_id, 7)
    balance = await services.finance.balance(user_id)
    sub = await services.subscription.get_subscription(user_id)
    can_ai, remaining = await services.subscription.can_use_ai(user, sub)
    is_active = services.subscription.is_active(sub)

    next_event = None
    if events:
        ce = events[0].calendar_event
        next_event = {
            "title": ce.title if ce else "Событие",
            "due_date": events[0].due_date.isoformat(),
        }

    return {
        "has_profile": True,
        "user_id": user_id,
        "profile": _serialize_profile(profile),
        "balance": balance,
        "next_event": next_event,
        "subscription_active": is_active,
        "remaining_ai": remaining,
    }


@router.get("/users/{telegram_id}/profile")
async def user_profile(telegram_id: int, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    profile = await services.onboarding.load_profile(str(user.id))
    if profile is None:
        return {"has_profile": False, "user_id": str(user.id)}
    return {"has_profile": True, "user_id": str(user.id), "profile": _serialize_profile(profile)}


@router.get("/events/{telegram_id}/list")
async def events_list(telegram_id: int, days: int = 14, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    events = await services.calendar.upcoming(str(user.id), days)
    return {"events": [_serialize_event(e) for e in events]}


@router.get("/events/{telegram_id}/calendar")
async def events_calendar(telegram_id: int, days: int = 30, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    events = await services.calendar.upcoming(str(user.id), days)
    return {"events": [_serialize_event(e) for e in events]}


@router.get("/events/{telegram_id}/overdue")
async def events_overdue(telegram_id: int, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    events = await services.calendar.overdue(str(user.id))
    overdue = [e for e in events if e.due_date < date.today()]
    return {"events": [_serialize_event(e) for e in overdue]}


@router.post("/events/{user_event_id}/snooze")
async def event_snooze(user_event_id: str, services=Depends(get_services_dep)):
    await services.calendar.calendar_repo.snooze(user_event_id, utcnow() + timedelta(days=1))
    return {"ok": True}


@router.post("/events/{user_event_id}/complete")
async def event_complete(user_event_id: str, services=Depends(get_services_dep)):
    await services.calendar.calendar_repo.mark_completed(user_event_id, utcnow())
    return {"ok": True}


@router.get("/finance/{telegram_id}/report")
async def finance_report(telegram_id: int, days: int = 30, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    user_id = str(user.id)
    profile = await services.onboarding.load_profile(user_id)
    report = await services.finance.report(user_id, date.today() - timedelta(days=days), date.today())

    tax_base = report["totals"]["income"]
    if profile is not None and profile.tax_regime.value == "usn_income_expense":
        tax_base = report["profit"]

    return {
        "income": float(report["totals"]["income"]),
        "expense": float(report["totals"]["expense"]),
        "profit": float(report["profit"]),
        "tax_base": float(tax_base),
        "top_expenses": [
            {"category": cat, "amount": float(amt)}
            for cat, amt in (report.get("top_expenses") or [])[:3]
        ],
    }


@router.get("/finance/{telegram_id}/balance")
async def finance_balance(telegram_id: int, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    balance = await services.finance.balance(str(user.id))
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in balance.items()}


@router.get("/finance/{telegram_id}/records")
async def finance_records(
    telegram_id: int, record_type: str = "all", limit: int = 20, services=Depends(get_services_dep),
):
    from shared.db.enums import FinanceRecordType

    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    user_id = str(user.id)

    if record_type == "income":
        records = await services.finance.list_records(user_id, record_type=FinanceRecordType.INCOME, limit=limit)
    elif record_type == "expense":
        records = await services.finance.list_records(user_id, record_type=FinanceRecordType.EXPENSE, limit=limit)
    else:
        inc = await services.finance.list_records(user_id, record_type=FinanceRecordType.INCOME, limit=limit)
        exp = await services.finance.list_records(user_id, record_type=FinanceRecordType.EXPENSE, limit=limit)
        records = sorted(inc + exp, key=lambda r: r.operation_date, reverse=True)[:limit]

    return {
        "records": [
            {
                "id": str(r.id),
                "record_type": r.record_type.value,
                "amount": str(r.amount),
                "category": r.category,
                "operation_date": r.operation_date.isoformat(),
                "source_text": r.source_text,
            }
            for r in records
        ],
    }


@router.post("/finance/{telegram_id}/add-from-text")
async def finance_add_from_text(
    telegram_id: int, req: AddFromTextRequest, services=Depends(get_services_dep),
):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    try:
        record = await services.finance.add_from_text(str(user.id), req.source_text)
    except ValueError:
        return {"ok": False, "error": "parse_failed"}
    if record is None:
        return {"ok": False, "error": "parse_failed"}
    return {
        "ok": True,
        "record_type": record.record_type.value,
        "amount": str(record.amount),
        "category": record.category,
    }


@router.get("/users/{telegram_id}/documents")
async def user_documents(telegram_id: int, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    documents = await services.documents.upcoming_documents(str(user.id))
    return {"documents": documents or []}


@router.get("/users/{telegram_id}/laws")
async def user_laws(telegram_id: int, min_importance: int = 70, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    profile = await services.onboarding.load_profile(str(user.id))
    if profile is None:
        return {"has_profile": False, "updates": []}

    from backend.services.profile_matching import ProfileContext

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
        "has_profile": True,
        "updates": [
            {
                "id": str(u.id),
                "title": u.title,
                "source": u.source,
                "effective_date": u.effective_date.isoformat() if u.effective_date else None,
                "action_required": u.action_required,
            }
            for u in (updates or [])[:5]
        ],
    }


@router.get("/users/{telegram_id}/reminders")
async def user_reminders(telegram_id: int, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    profile = await services.onboarding.load_profile(str(user.id))
    if profile is None:
        return {"has_profile": False}
    return {"has_profile": True, "reminder_settings": profile.reminder_settings or {}}


@router.get("/ai/{telegram_id}/history")
async def ai_history(telegram_id: int, limit: int = 5, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    from shared.db.session import SessionFactory
    from shared.db.models import AIDialog
    from sqlalchemy import select, desc

    async with SessionFactory() as session:
        result = await session.execute(
            select(AIDialog)
            .where(AIDialog.user_id == user.id)
            .order_by(desc(AIDialog.created_at))
            .limit(limit)
        )
        dialogs = list(reversed(result.scalars().all()))

    history = []
    for d in dialogs:
        history.append({"role": "user", "content": d.question})
        history.append({"role": "assistant", "content": d.answer})
    return {"history": history}


@router.delete("/ai/{telegram_id}/history")
async def ai_clear_history(telegram_id: int, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    from shared.db.session import SessionFactory
    from shared.db.models import AIDialog
    from sqlalchemy import delete

    async with SessionFactory() as session:
        await session.execute(delete(AIDialog).where(AIDialog.user_id == user.id))
        await session.commit()
    return {"ok": True}


@router.post("/ai/{telegram_id}/dialog")
async def ai_save_dialog(telegram_id: int, req: SaveDialogRequest, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    from shared.db.session import SessionFactory
    from shared.db.models import AIDialog

    async with SessionFactory() as session:
        from backend.services.container import build_services

        svcs = build_services(session)
        session.add(AIDialog(user_id=user.id, question=req.question, answer=req.answer, sources=req.sources))
        await svcs.subscription.increment_ai_usage(user)
        await session.commit()
        sub = await svcs.subscription.get_subscription(str(user.id))
        is_active = svcs.subscription.is_active(sub)
        _, remaining = await svcs.subscription.can_use_ai(user, sub)
    return {"ok": True, "remaining_ai": remaining, "subscription_active": is_active}


@router.post("/ai/{telegram_id}/full-question")
async def ai_full_question(telegram_id: int, req: SaveDialogRequest, services=Depends(get_services_dep)):
    """Complete AI flow: check limits, get history, call AI, save dialog, return answer."""
    settings = get_settings()
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    user_id = str(user.id)
    sub = await services.subscription.get_subscription(user_id)
    can_use, remaining = await services.subscription.can_use_ai(user, sub)

    if not can_use:
        return {"ok": False, "error": "paywall", "remaining_ai": 0}

    from backend.services.rate_limit import allow_ai_request

    if not await allow_ai_request(settings, user_id):
        return {"ok": False, "error": "rate_limit"}

    profile = await services.onboarding.load_profile(user_id)

    from shared.db.session import SessionFactory
    from shared.db.models import AIDialog
    from sqlalchemy import select, desc

    async with SessionFactory() as session:
        result = await session.execute(
            select(AIDialog)
            .where(AIDialog.user_id == user.id)
            .order_by(desc(AIDialog.created_at))
            .limit(5)
        )
        dialogs = list(reversed(result.scalars().all()))
        history = []
        for d in dialogs:
            history.append({"role": "user", "content": d.question})
            history.append({"role": "assistant", "content": d.answer})

    profile_data = {}
    if profile:
        profile_data = {
            "entity_type": profile.entity_type.value if profile.entity_type else None,
            "tax_regime": profile.tax_regime.value if profile.tax_regime else None,
            "has_employees": profile.has_employees if profile else None,
        }

    response = await services.ai.answer_tax_question(req.question, profile_data, history=history)

    async with SessionFactory() as session:
        from backend.services.container import build_services as bs

        svcs = bs(session)
        session.add(AIDialog(user_id=user.id, question=req.question, answer=response.text, sources=response.sources))
        await svcs.subscription.increment_ai_usage(user)
        await session.commit()
        sub2 = await svcs.subscription.get_subscription(user_id)
        is_active = svcs.subscription.is_active(sub2)
        _, new_remaining = await svcs.subscription.can_use_ai(user, sub2)

    return {
        "ok": True,
        "answer": response.text,
        "sources": response.sources,
        "remaining_ai": new_remaining,
        "subscription_active": is_active,
    }


@router.get("/subscription/{telegram_id}/full-status")
async def subscription_full_status(telegram_id: int, services=Depends(get_services_dep)):
    settings = get_settings()
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    sub = await services.subscription.get_subscription(str(user.id))
    is_active = services.subscription.is_active(sub)
    can_ai, remaining = await services.subscription.can_use_ai(user, sub)

    from backend.services.subscription import PLAN_DETAILS

    result = {
        "is_active": is_active,
        "can_ai": can_ai,
        "remaining_ai": remaining,
        "prices": {
            "basic": settings.stars_price_basic,
            "pro": settings.stars_price_pro,
            "annual": settings.stars_price_annual,
        },
    }
    if is_active and sub:
        plan_details = PLAN_DETAILS.get(sub.plan, {})
        result["plan_label"] = plan_details.get("label", "Активна")
        result["expires_at"] = sub.expires_at.strftime("%d.%m.%Y") if sub.expires_at else None
    return result


@router.post("/subscription/{telegram_id}/cancel")
async def subscription_cancel(telegram_id: int, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    await services.subscription.cancel(str(user.id))
    return {"ok": True}


@router.post("/subscription/{telegram_id}/activate")
async def subscription_activate(telegram_id: int, plan: str = "basic", services=Depends(get_services_dep)):
    from shared.db.enums import SubscriptionPlan

    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    plan_enum = SubscriptionPlan(plan)
    sub = await services.subscription.activate(str(user.id), plan_enum)

    from backend.services.subscription import PLAN_DETAILS

    details = PLAN_DETAILS.get(plan_enum, {})
    return {
        "ok": True,
        "plan_label": details.get("label", plan),
        "expires_at": sub.expires_at.strftime("%d.%m.%Y") if sub.expires_at else None,
    }


@router.post("/subscription/{telegram_id}/record-payment")
async def subscription_record_payment(
    telegram_id: int, req: RecordPaymentRequest, services=Depends(get_services_dep),
):
    from shared.db.enums import SubscriptionPlan

    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    user_id = str(user.id)
    plan_enum = SubscriptionPlan(req.plan)

    exists = await services.subscription.payment_exists(req.charge_id)
    if exists:
        return {"ok": False, "error": "already_processed"}

    sub = await services.subscription.activate(user_id, plan_enum)
    await services.subscription.record_payment(user_id, plan_enum, req.amount, req.charge_id)

    from backend.services.subscription import PLAN_DETAILS

    details = PLAN_DETAILS.get(plan_enum, {})
    return {
        "ok": True,
        "plan_label": details.get("label", req.plan),
        "expires_at": sub.expires_at.strftime("%d.%m.%Y") if sub.expires_at else None,
    }


@router.get("/users/{telegram_id}/referral")
async def user_referral(telegram_id: int, services=Depends(get_services_dep)):
    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    from shared.db.session import SessionFactory
    from shared.db.models import User
    from sqlalchemy import select, func

    async with SessionFactory() as session:
        result = await session.execute(
            select(func.count()).select_from(User).where(User.referred_by == str(telegram_id))
        )
        ref_count = result.scalar() or 0
    return {
        "referral_count": ref_count,
        "bonus_requests": user.referral_bonus_requests,
    }


@router.post("/users/{telegram_id}/referral")
async def save_referral(telegram_id: int, req: ReferralRequest, services=Depends(get_services_dep)):
    from shared.db.session import SessionFactory
    from shared.db.models import User
    from sqlalchemy import select

    async with SessionFactory() as session:
        from backend.services.container import build_services

        svcs = build_services(session)
        user = await svcs.onboarding.ensure_user(
            telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
        )
        if user.referred_by is None and str(telegram_id) != req.referrer_telegram_id:
            user.referred_by = req.referrer_telegram_id
            result = await session.execute(
                select(User).where(User.telegram_id == int(req.referrer_telegram_id))
            )
            referrer = result.scalar_one_or_none()
            if referrer:
                referrer.referral_bonus_requests += 3
            await session.commit()
    return {"ok": True}


@router.post("/users/{telegram_id}/onboarding-with-sync")
async def onboarding_with_sync(
    telegram_id: int, req: OnboardingWithSyncRequest, services=Depends(get_services_dep),
):
    from shared.db.session import SessionFactory
    from backend.services.container import build_services
    from backend.services.onboarding import OnboardingDraft
    from backend.services.profile_matching import ProfileContext
    from shared.db.enums import EntityType, TaxRegime

    async with SessionFactory() as session:
        svcs = build_services(session)
        user = await svcs.onboarding.ensure_user(
            telegram_id=telegram_id, username=None, first_name=None, timezone=req.timezone,
        )
        draft = OnboardingDraft(
            entity_type=EntityType(req.entity_type),
            tax_regime=TaxRegime(req.tax_regime),
            has_employees=req.has_employees,
            marketplaces_enabled=req.marketplaces_enabled,
            industry=req.industry,
            region=req.region,
            timezone=req.timezone,
            reminder_settings=req.reminder_settings,
        )
        await svcs.onboarding.save_profile(str(user.id), draft)
        profile_context = ProfileContext(
            entity_type=draft.entity_type,
            tax_regime=draft.tax_regime,
            has_employees=draft.has_employees,
            marketplaces_enabled=draft.marketplaces_enabled,
            region=draft.region,
            industry=draft.industry,
            reminder_offsets=draft.reminder_settings.get("offset_days", [3, 1]),
        )
        await svcs.calendar.sync_user_events(str(user.id), profile_context)
        user_events = await svcs.calendar.upcoming(str(user.id), 370)
        for user_event in user_events:
            await svcs.reminders.create_reminders_for_event(
                user_event, draft.reminder_settings, draft.timezone,
            )
        await session.commit()
    return {"ok": True}


@router.post("/tax/compare-regimes")
async def tax_compare_regimes(req: CompareRegimesRequest):
    try:
        monthly_income = Decimal(req.monthly_income)
    except (InvalidOperation, ValueError):
        return {"ok": False, "error": "invalid_income"}
    from backend.services.tax_engine import TaxCalculatorService

    svc = TaxCalculatorService()
    result = svc.compare_regimes(
        activity=req.activity,
        monthly_income=monthly_income,
        has_employees=req.has_employees,
        counterparties=req.counterparties,
        region=req.region,
    )
    return {"ok": True, "rendered": result.render()}


@router.post("/tax/parse-and-calculate")
async def tax_parse_and_calculate(telegram_id: int, query: str, services=Depends(get_services_dep)):
    from backend.services.tax_engine import TaxQueryParser, TaxCalculatorService

    user = await services.onboarding.ensure_user(
        telegram_id=telegram_id, username=None, first_name=None, timezone="Europe/Moscow",
    )
    profile = await services.onboarding.load_profile(str(user.id))
    profile_data = {
        "entity_type": profile.entity_type.value if profile else None,
        "tax_regime": profile.tax_regime.value if profile else None,
        "has_employees": profile.has_employees if profile else False,
    }

    if not TaxQueryParser.looks_like_calculation_request(query):
        return {"ok": False, "is_calculation": False}

    parsed = TaxQueryParser.parse(query, profile_data)
    if parsed.question:
        return {"ok": True, "is_calculation": True, "question": parsed.question, "result": None}
    if parsed.request is None:
        return {"ok": False, "is_calculation": False}

    result = TaxCalculatorService.calculate(parsed.request)
    return {"ok": True, "is_calculation": True, "question": None, "result": result.render()}


@router.post("/templates/match")
async def match_template(req: MatchTemplateRequest, services=Depends(get_services_dep)):
    template = services.templates.match_template(req.text)
    if template is None:
        return {"matched": False}
    return {"matched": True, "response": template}


# ── Helpers ─────────────────────────────────────────────────────


def _serialize_profile(profile) -> dict:
    return {
        "entity_type": profile.entity_type.value if profile.entity_type else None,
        "tax_regime": profile.tax_regime.value if profile.tax_regime else None,
        "has_employees": profile.has_employees,
        "marketplaces_enabled": profile.marketplaces_enabled,
        "region": profile.region,
        "industry": getattr(profile, "industry", None),
        "reminder_settings": profile.reminder_settings or {},
    }


def _serialize_event(ue) -> dict:
    ce = ue.calendar_event
    return {
        "user_event_id": str(ue.id),
        "title": ce.title if ce else "Событие",
        "description": ce.description if ce else "",
        "category": ce.category.value if ce else "",
        "due_date": ue.due_date.isoformat(),
        "status": ue.status.value,
    }


def _serialize_subscription(services, sub, user) -> dict:
    is_active = services.subscription.is_active(sub)
    return {
        "is_active": is_active,
        "plan": sub.plan.value if sub else None,
        "expires_at": sub.expires_at.isoformat() if sub and sub.expires_at else None,
    }
