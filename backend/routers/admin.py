from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, or_, select

from shared.config import Settings, get_settings
from shared.db.enums import LawUpdateReviewStatus, PaymentStatus, SubscriptionPlan
from shared.db.models import (
    AIDialog,
    AdminLog,
    BusinessProfile,
    LawUpdate,
    Payment,
    Reminder,
    Subscription,
    User,
    UserActivity,
)
from shared.db.session import SessionFactory
from backend.services.container import build_services
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError


def build_admin_router() -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])

    class AdminContext(BaseModel):
        settings: Settings
        actor: str
        role: str

    ROLE_LEVELS = {
        "viewer": 10,
        "support": 20,
        "admin": 30,
        "owner": 40,
    }

    def require_role(ctx: AdminContext, min_role: str) -> None:
        if ROLE_LEVELS.get(ctx.role, 0) < ROLE_LEVELS.get(min_role, 0):
            raise HTTPException(status_code=403, detail="Insufficient role")

    def require_admin(
        request: Request,
        x_admin_token: str = Header(default=""),
        x_admin_actor: str = Header(default=""),
        settings: Settings = Depends(get_settings),
    ) -> AdminContext:
        role = None
        if x_admin_token == settings.admin_api_token and settings.admin_api_token:
            role = "owner"
        elif x_admin_token in settings.admin_tokens:
            role = settings.admin_tokens[x_admin_token]
        if role is None:
            raise HTTPException(status_code=403, detail="Forbidden")
        if settings.admin_allowed_ips:
            client_ip = request.client.host if request.client else ""
            if client_ip not in settings.admin_allowed_ips:
                raise HTTPException(status_code=403, detail="Forbidden")
        actor = x_admin_actor or "admin"
        return AdminContext(settings=settings, actor=actor, role=role)

    async def log_admin(session, action: str, actor: str, payload: dict) -> None:
        session.add(AdminLog(action=action, actor=actor, payload=payload))

    @router.get("/overview")
    async def overview(ctx: AdminContext = Depends(require_admin)) -> dict:
        require_role(ctx, "viewer")
        async with SessionFactory() as session:
            users = await session.scalar(select(func.count()).select_from(User))
            profiles = await session.scalar(select(func.count()).select_from(BusinessProfile))
            reminders = await session.scalar(select(func.count()).select_from(Reminder))
            pending_updates = await session.scalar(select(func.count()).select_from(LawUpdate))
        return {
            "users": users or 0,
            "profiles": profiles or 0,
            "reminders": reminders or 0,
            "law_updates": pending_updates or 0,
        }

    @router.get("/law-updates/pending")
    async def pending_law_updates(ctx: AdminContext = Depends(require_admin)) -> list:
        require_role(ctx, "support")
        async with SessionFactory() as session:
            result = await session.execute(select(LawUpdate).order_by(LawUpdate.published_at.desc()).limit(20))
            updates = result.scalars().all()
        return [
            {
                "id": str(item.id),
                "title": item.title,
                "source": item.source,
                "importance_score": item.importance_score,
                "review_status": item.review_status.value,
            }
            for item in updates
        ]

    class LawUpdateCreate(BaseModel):
        source: str
        source_url: str
        title: str
        summary: str
        published_at: datetime
        effective_date: datetime | None = None
        tags: list[str] = Field(default_factory=list)
        importance_score: int = 0
        affected_entity_types: list[str] = Field(default_factory=list)
        affected_tax_regimes: list[str] = Field(default_factory=list)
        affected_marketplaces: bool | None = None
        action_required: str | None = None
        review_status: str = "approved"

    @router.post("/law-updates")
    async def create_law_update(
        payload: LawUpdateCreate,
        ctx: AdminContext = Depends(require_admin),
    ) -> dict:
        require_role(ctx, "admin")
        review_status = LawUpdateReviewStatus(payload.review_status)
        async with SessionFactory() as session:
            update = LawUpdate(
                source=payload.source,
                source_url=payload.source_url,
                title=payload.title,
                summary=payload.summary,
                full_text=None,
                published_at=payload.published_at,
                effective_date=payload.effective_date.date() if payload.effective_date else None,
                tags=payload.tags,
                importance_score=payload.importance_score,
                affected_entity_types=payload.affected_entity_types,
                affected_tax_regimes=payload.affected_tax_regimes,
                affected_marketplaces=payload.affected_marketplaces,
                action_required=payload.action_required,
                is_active=True,
                review_status=review_status,
            )
            session.add(update)
            await log_admin(session, "law_update_create", ctx.actor, {"title": payload.title})
            await session.commit()
        return {"id": str(update.id), "status": "created"}

    class UserSubscriptionAction(BaseModel):
        action: str = Field(description="grant | cancel | set_plan")
        plan: str | None = None
        days: int | None = None

    @router.get("/users")
    async def list_users(
        q: str | None = None,
        status: str | None = None,
        subscribed: bool | None = None,
        limit: int = 50,
        offset: int = 0,
        ctx: AdminContext = Depends(require_admin),
    ) -> dict:
        require_role(ctx, "viewer")
        async with SessionFactory() as session:
            stmt = select(User, Subscription).outerjoin(Subscription, Subscription.user_id == User.id)
            if q:
                if q.isdigit():
                    stmt = stmt.where(User.telegram_id == int(q))
                else:
                    like = f"%{q.lower()}%"
                    stmt = stmt.where(
                        or_(
                            func.lower(User.username).like(like),
                            func.lower(User.first_name).like(like),
                        )
                    )
            if status == "active":
                stmt = stmt.where(User.is_active.is_(True))
            elif status == "inactive":
                stmt = stmt.where(User.is_active.is_(False))
            if subscribed is True:
                stmt = stmt.where(Subscription.plan != SubscriptionPlan.FREE)
            elif subscribed is False:
                stmt = stmt.where(or_(Subscription.plan.is_(None), Subscription.plan == SubscriptionPlan.FREE))

            stmt = stmt.order_by(desc(User.created_at)).limit(limit).offset(offset)
            rows = (await session.execute(stmt)).all()

        return {
            "items": [
                {
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "last_seen_at": user.last_seen_at,
                    "plan": sub.plan.value if sub else "free",
                    "expires_at": sub.expires_at if sub else None,
                }
                for user, sub in rows
            ],
            "limit": limit,
            "offset": offset,
        }

    @router.get("/users/{telegram_id}")
    async def user_card(telegram_id: int, ctx: AdminContext = Depends(require_admin)) -> dict:
        require_role(ctx, "support")
        async with SessionFactory() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")
            profile = await session.scalar(select(BusinessProfile).where(BusinessProfile.user_id == user.id))
            subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
            payments = (await session.execute(
                select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc()).limit(20)
            )).scalars().all()
            ai_count = await session.scalar(select(func.count()).select_from(AIDialog).where(AIDialog.user_id == user.id))

        return {
            "user": {
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "created_at": user.created_at,
                "last_seen_at": user.last_seen_at,
                "is_active": user.is_active,
                "deactivated_at": user.deactivated_at,
                "reactivated_at": user.reactivated_at,
                "ai_requests_today": user.ai_requests_today,
            },
            "profile": {
                "entity_type": profile.entity_type.value if profile else None,
                "tax_regime": profile.tax_regime.value if profile else None,
                "has_employees": profile.has_employees if profile else None,
                "region": profile.region if profile else None,
                "industry": profile.industry if profile else None,
            },
            "subscription": {
                "plan": subscription.plan.value if subscription else "free",
                "expires_at": subscription.expires_at if subscription else None,
                "auto_renew": subscription.auto_renew if subscription else None,
            },
            "payments": [
                {
                    "amount_stars": p.amount_stars,
                    "plan": p.plan.value,
                    "status": p.status.value,
                    "created_at": p.created_at,
                    "telegram_payment_id": p.telegram_payment_id,
                }
                for p in payments
            ],
            "ai_dialogs": ai_count or 0,
        }

    @router.post("/users/{telegram_id}/subscription")
    async def manage_subscription(
        telegram_id: int,
        payload: UserSubscriptionAction,
        ctx: AdminContext = Depends(require_admin),
    ) -> dict:
        require_role(ctx, "admin")
        async with SessionFactory() as session:
            services = build_services(session)
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")
            action = payload.action
            if action == "cancel":
                sub = await services.subscription.cancel(str(user.id))
            elif action == "grant":
                if not payload.plan or not payload.days:
                    raise HTTPException(status_code=400, detail="plan and days required")
                sub = await services.subscription.grant(str(user.id), SubscriptionPlan(payload.plan), payload.days)
            elif action == "set_plan":
                if not payload.plan:
                    raise HTTPException(status_code=400, detail="plan required")
                sub = await services.subscription.activate(str(user.id), SubscriptionPlan(payload.plan))
            else:
                raise HTTPException(status_code=400, detail="Unknown action")
            await log_admin(session, "subscription_change", ctx.actor, {"user": telegram_id, "action": action})
            await session.commit()
        return {"status": "ok", "plan": sub.plan.value, "expires_at": sub.expires_at}

    @router.post("/users/{telegram_id}/ban")
    async def ban_user(telegram_id: int, ctx: AdminContext = Depends(require_admin)) -> dict:
        require_role(ctx, "admin")
        async with SessionFactory() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")
            user.is_active = False
            user.deactivated_at = datetime.now(timezone.utc)
            await log_admin(session, "user_ban", ctx.actor, {"user": telegram_id})
            await session.commit()
        return {"status": "ok"}

    @router.post("/users/{telegram_id}/unban")
    async def unban_user(telegram_id: int, ctx: AdminContext = Depends(require_admin)) -> dict:
        require_role(ctx, "admin")
        async with SessionFactory() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")
            user.is_active = True
            user.reactivated_at = datetime.now(timezone.utc)
            await log_admin(session, "user_unban", ctx.actor, {"user": telegram_id})
            await session.commit()
        return {"status": "ok"}

    @router.get("/payments")
    async def list_payments(
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        ctx: AdminContext = Depends(require_admin),
    ) -> dict:
        require_role(ctx, "admin")
        async with SessionFactory() as session:
            stmt = select(Payment).order_by(desc(Payment.created_at)).limit(limit).offset(offset)
            if status:
                stmt = stmt.where(Payment.status == PaymentStatus(status))
            payments = (await session.execute(stmt)).scalars().all()
        return {
            "items": [
                {
                    "user_id": p.user_id,
                    "plan": p.plan.value,
                    "amount_stars": p.amount_stars,
                    "status": p.status.value,
                    "created_at": p.created_at,
                    "telegram_payment_id": p.telegram_payment_id,
                }
                for p in payments
            ]
        }

    @router.get("/metrics/overview")
    async def metrics_overview(ctx: AdminContext = Depends(require_admin)) -> dict:
        require_role(ctx, "viewer")
        async with SessionFactory() as session:
            now = datetime.now(timezone.utc)
            total_users = await session.scalar(select(func.count()).select_from(User))
            active_1d = await session.scalar(select(func.count()).select_from(User).where(User.last_seen_at >= now - timedelta(days=1)))
            active_7d = await session.scalar(select(func.count()).select_from(User).where(User.last_seen_at >= now - timedelta(days=7)))
            active_30d = await session.scalar(select(func.count()).select_from(User).where(User.last_seen_at >= now - timedelta(days=30)))
            new_1d = await session.scalar(select(func.count()).select_from(User).where(User.created_at >= now - timedelta(days=1)))
            new_7d = await session.scalar(select(func.count()).select_from(User).where(User.created_at >= now - timedelta(days=7)))
            new_30d = await session.scalar(select(func.count()).select_from(User).where(User.created_at >= now - timedelta(days=30)))
            inactive = await session.scalar(select(func.count()).select_from(User).where(User.is_active.is_(False)))

            subs = (await session.execute(select(Subscription))).scalars().all()
            price_map = {
                SubscriptionPlan.BASIC: ctx.settings.stars_price_basic,
                SubscriptionPlan.PRO: ctx.settings.stars_price_pro,
                SubscriptionPlan.ANNUAL: ctx.settings.stars_price_annual,
            }
            mrr = 0
            paid_active = 0
            for sub in subs:
                if sub.plan != SubscriptionPlan.FREE and sub.expires_at and sub.expires_at > now:
                    paid_active += 1
                    mrr += price_map.get(sub.plan, 0)

            paid_last_30 = await session.scalar(
                select(func.count()).select_from(Payment).where(Payment.created_at >= now - timedelta(days=30))
            )
            revenue_last_30 = await session.scalar(
                select(func.coalesce(func.sum(Payment.amount_stars), 0)).select_from(Payment)
                .where(Payment.status == PaymentStatus.COMPLETED)
                .where(Payment.created_at >= now - timedelta(days=30))
            )

        stickiness = 0.0
        if active_30d:
            stickiness = round((active_1d or 0) / active_30d, 3)

        return {
            "total_users": total_users or 0,
            "active_1d": active_1d or 0,
            "active_7d": active_7d or 0,
            "active_30d": active_30d or 0,
            "dau_mau": stickiness,
            "new_1d": new_1d or 0,
            "new_7d": new_7d or 0,
            "new_30d": new_30d or 0,
            "inactive": inactive or 0,
            "paid_active": paid_active,
            "mrr_stars": mrr,
            "payments_30d": paid_last_30 or 0,
            "revenue_30d_stars": revenue_last_30 or 0,
        }

    @router.get("/metrics/usage")
    async def metrics_usage(ctx: AdminContext = Depends(require_admin)) -> dict:
        require_role(ctx, "viewer")
        async with SessionFactory() as session:
            now = datetime.now(timezone.utc)
            stmt = (
                select(
                    func.date_trunc("day", UserActivity.created_at).label("day"),
                    UserActivity.event_type,
                    func.count().label("count"),
                )
                .where(UserActivity.created_at >= now - timedelta(days=30))
                .group_by("day", UserActivity.event_type)
                .order_by("day")
            )
            rows = (await session.execute(stmt)).all()
        return {
            "series": [
                {"day": row.day.date().isoformat(), "event_type": row.event_type, "count": row.count}
                for row in rows
            ]
        }

    @router.get("/metrics/ai")
    async def metrics_ai(ctx: AdminContext = Depends(require_admin)) -> dict:
        require_role(ctx, "viewer")
        async with SessionFactory() as session:
            now = datetime.now(timezone.utc)
            stmt = (
                select(
                    func.date_trunc("day", AIDialog.created_at).label("day"),
                    func.count().label("count"),
                )
                .where(AIDialog.created_at >= now - timedelta(days=30))
                .group_by("day")
                .order_by("day")
            )
            rows = (await session.execute(stmt)).all()
        return {
            "series": [{"day": row.day.date().isoformat(), "count": row.count} for row in rows]
        }

    @router.get("/logs")
    async def admin_logs(limit: int = 50, ctx: AdminContext = Depends(require_admin)) -> dict:
        require_role(ctx, "admin")
        async with SessionFactory() as session:
            logs = (await session.execute(
                select(AdminLog).order_by(desc(AdminLog.created_at)).limit(limit)
            )).scalars().all()
        return {
            "items": [
                {"action": log.action, "actor": log.actor, "payload": log.payload, "created_at": log.created_at}
                for log in logs
            ]
        }

    class BroadcastPayload(BaseModel):
        segment: str = Field(description="all | active | paid")
        text: str
        limit: int = 200
        dry_run: bool = False

    @router.post("/broadcast")
    async def broadcast(payload: BroadcastPayload, ctx: AdminContext = Depends(require_admin)) -> dict:
        require_role(ctx, "admin")
        bot = Bot(token=ctx.settings.telegram_bot_token)
        sent = 0
        failed = 0
        async with SessionFactory() as session:
            users_stmt = select(User).order_by(desc(User.created_at))
            if payload.segment == "active":
                users_stmt = users_stmt.where(User.is_active.is_(True))
            users = (await session.execute(users_stmt.limit(payload.limit))).scalars().all()
            count = len(users)
            if not payload.dry_run:
                for user in users:
                    try:
                        await bot.send_message(chat_id=user.telegram_id, text=payload.text)
                        sent += 1
                    except TelegramForbiddenError:
                        user.is_active = False
                        user.deactivated_at = datetime.now(timezone.utc)
                        failed += 1
                    except Exception:
                        failed += 1
            await log_admin(
                session,
                "broadcast",
                ctx.actor,
                {"segment": payload.segment, "count": count, "sent": sent, "failed": failed, "dry_run": payload.dry_run},
            )
            await session.commit()
        await bot.session.close()
        return {"status": "ok", "count": count, "sent": sent, "failed": failed}

    return router
