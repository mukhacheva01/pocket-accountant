from typing import Optional
from secrets import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import func, select

from accountant_bot.core.config import Settings
from accountant_bot.db.models import BusinessProfile, LawUpdate, Reminder, User
from accountant_bot.db.session import SessionFactory
from accountant_bot.services.container import build_services


def build_admin_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])

    def resolve_client_ip(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip", "").strip()
        if forwarded_for:
            return forwarded_for
        if real_ip:
            return real_ip
        return request.client.host if request.client else ""

    def require_admin(request: Request, x_admin_token: str = Header(default="")) -> Settings:
        if not settings.admin_api_enabled:
            raise HTTPException(status_code=503, detail="Admin API is disabled")
        if not compare_digest(x_admin_token or "", settings.admin_api_token):
            raise HTTPException(status_code=403, detail="Forbidden")
        if settings.admin_allowed_ips:
            client_ip = resolve_client_ip(request)
            if client_ip not in settings.admin_allowed_ips:
                raise HTTPException(status_code=403, detail="Forbidden")
        return settings

    @router.get("/overview")
    async def overview(_: Settings = Depends(require_admin)) -> dict:
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
    async def pending_law_updates(_: Settings = Depends(require_admin)) -> list:
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

    @router.get("/ozon/connections")
    async def ozon_connections(_: Settings = Depends(require_admin)) -> list:
        async with SessionFactory() as session:
            services = build_services(session)
            connections = await services.marketplace_connections.connections.list_all(provider="ozon")
        return [
            {
                "user_id": str(item.user_id),
                "seller_id": item.seller_id,
                "status": item.status,
                "ads_status": item.ads_status,
                "ads_api_key_masked": item.ads_api_key_masked,
                "synced_cards": item.synced_cards,
                "synced_price_snapshots": (item.sync_meta or {}).get("synced_price_snapshots", 0),
                "synced_orders": item.synced_orders,
                "synced_stocks": item.synced_stocks,
                "synced_ads_campaigns": (item.sync_meta or {}).get("synced_ads_campaigns", 0),
                "last_synced_at": item.last_synced_at.isoformat() if item.last_synced_at else None,
                "ads_last_synced_at": item.ads_last_synced_at.isoformat() if item.ads_last_synced_at else None,
                "last_error": item.last_error,
                "ads_last_error": item.ads_last_error,
            }
            for item in connections
        ]

    @router.post("/ozon/sync")
    async def run_ozon_sync(user_id: Optional[str] = None, _: Settings = Depends(require_admin)) -> dict:
        async with SessionFactory() as session:
            services = build_services(session)
            if user_id:
                result = await services.ozon_sync.sync_user_connection(user_id)
                await session.commit()
                return {"result": None if result is None else result.__dict__}
            results = await services.ozon_sync.sync_all_connections()
            await session.commit()
        return {"results": [item.__dict__ for item in results]}

    return router
