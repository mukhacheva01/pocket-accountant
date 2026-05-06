import logging
from secrets import compare_digest
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from accountant_bot.admin.router import build_admin_router
from accountant_bot.bot.runtime import build_bot, build_dispatcher
from accountant_bot.core.config import Settings, get_settings
from accountant_bot.core.logging import configure_logging
from accountant_bot.db.models import MarketplaceConnection, User
from accountant_bot.db.session import SessionFactory
from accountant_bot.repositories.backend_events import BackendEventReceiptRepository
from accountant_bot.repositories.marketplace_connections import MarketplaceConnectionRepository
from accountant_bot.services.backend_events import BackendEventFormatter
from accountant_bot.services.container import build_services


logger = logging.getLogger(__name__)


class BackendNotification(BaseModel):
    text: str
    title: str = ""
    section: str = "sync"
    user_id: str = ""
    telegram_id: int = 0
    seller_id: str = ""


class BackendEventPayload(BaseModel):
    event_type: str
    user_id: str = ""
    telegram_id: int = 0
    seller_id: str = ""
    title: str = ""
    text: str = ""
    section: str = ""
    event_id: str = ""
    posting_number: str = ""
    order_number: str = ""
    status: str = ""
    scheme: str = ""
    offer_id: str = ""
    sku: str = ""
    quantity: int = 0
    present: int = 0
    reserved: int = 0
    review_id: str = ""
    question_id: str = ""
    rating: int = 0
    synced_cards: int = 0
    synced_orders: int = 0
    synced_stocks: int = 0
    synced_reviews: int = 0
    error: str = ""
    details: str = ""
    metadata: dict = Field(default_factory=dict)


def _resolve_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip", "").strip()
    if forwarded_for:
        return forwarded_for
    if real_ip:
        return real_ip
    return request.client.host if request.client else ""


def _assert_admin(token: str, settings: Settings, request: Optional[Request] = None) -> None:
    if not settings.admin_api_enabled:
        raise HTTPException(status_code=503, detail="Admin API is disabled")
    if not compare_digest(token or "", settings.admin_api_token):
        raise HTTPException(status_code=403, detail="Forbidden")
    if request is not None and settings.admin_allowed_ips:
        client_ip = _resolve_client_ip(request)
        if client_ip not in settings.admin_allowed_ips:
            raise HTTPException(status_code=403, detail="Forbidden")


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    if settings.telegram_bot_configured and settings.telegram_uses_webhook:
        if not settings.telegram_webhook_url:
            raise ValueError("TELEGRAM_WEBHOOK_URL is required when TELEGRAM_DELIVERY_MODE=webhook")
        if not settings.telegram_webhook_secret:
            raise ValueError("TELEGRAM_WEBHOOK_SECRET is required when TELEGRAM_DELIVERY_MODE=webhook")

    bot = build_bot(settings) if settings.telegram_bot_configured else None
    dispatcher = build_dispatcher(settings) if settings.telegram_bot_configured and settings.telegram_uses_webhook else None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if bot is None:
            logger.warning("api_started_without_bot_token")
            yield
            logger.info("api_stopped")
            return

        app.state.bot = bot
        app.state.dispatcher = dispatcher

        if settings.telegram_uses_polling:
            logger.info("api_started_polling_mode")
        elif settings.telegram_webhook_url and dispatcher is not None:
            await bot.set_webhook(url=settings.telegram_webhook_url, secret_token=settings.telegram_webhook_secret)
            logger.info("api_started_webhook_mode")
        else:
            logger.warning("api_started_without_webhook_url")

        try:
            yield
        finally:
            await bot.session.close()
            logger.info("api_stopped")

    docs_url = "/docs" if settings.api_docs_enabled else None
    redoc_url = "/redoc" if settings.api_docs_enabled else None
    openapi_url = "/openapi.json" if settings.api_docs_enabled else None
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    async def resolve_target_user(session, *, user_id: str = "", telegram_id: int = 0, seller_id: str = ""):
        if user_id:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
        if telegram_id:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            return result.scalar_one_or_none()
        if seller_id:
            result = await session.execute(
                select(User)
                .join(MarketplaceConnection, MarketplaceConnection.user_id == User.id)
                .where(MarketplaceConnection.seller_id == seller_id)
                .limit(1)
            )
            return result.scalar_one_or_none()
        return None

    async def deliver_backend_notification(*, user, services, bot, title: str, text: str, section: str) -> dict:
        profile = await services.onboarding.load_profile(str(user.id))
        settings_payload = getattr(profile, "reminder_settings", {}) or {}
        flag_by_section = {
            "sync": "notify_sync",
            "stocks": "notify_stocks",
            "orders": "notify_orders",
            "reviews": "notify_reviews",
        }
        flag_key = flag_by_section.get(section)
        if flag_key and not settings_payload.get(flag_key, True):
            return {"ok": True, "delivered": False, "reason": "notifications_disabled"}

        message_text = text if not title else f"{title}\n{text}"
        await bot.send_message(chat_id=user.telegram_id, text=message_text.strip())
        return {"ok": True, "delivered": True}

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/admin/health")
    async def admin_health(request: Request, x_admin_token: str = Header(default="")) -> dict:
        _assert_admin(x_admin_token, settings, request)
        return {"status": "ok", "service": settings.app_name}

    @app.post(settings.telegram_webhook_path)
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str = Header(default=""),
    ) -> dict:
        if not settings.telegram_uses_webhook:
            raise HTTPException(status_code=503, detail="Webhook delivery mode is disabled")
        bot = getattr(request.app.state, "bot", None)
        dispatcher = getattr(request.app.state, "dispatcher", None)
        if bot is None or dispatcher is None:
            raise HTTPException(status_code=503, detail="Telegram bot runtime is not configured")
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Forbidden")
        payload = await request.json()
        update = Update.model_validate(payload, context={"bot": bot})
        await dispatcher.feed_update(bot, update)
        return {"ok": True}

    @app.post("/backend/notify")
    async def backend_notify(payload: BackendNotification, request: Request, x_admin_token: str = Header(default="")) -> dict:
        _assert_admin(x_admin_token, settings, request)
        bot = getattr(app.state, "bot", None)
        if bot is None:
            raise HTTPException(status_code=503, detail="Telegram bot runtime is not configured")

        async with SessionFactory() as session:
            user = await resolve_target_user(
                session,
                user_id=payload.user_id,
                telegram_id=payload.telegram_id,
                seller_id=payload.seller_id,
            )
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")

            services = build_services(session)
            return await deliver_backend_notification(
                user=user,
                services=services,
                bot=bot,
                title=payload.title,
                text=payload.text,
                section=payload.section or "sync",
            )

    @app.post("/backend/events/ozon")
    async def backend_ozon_event(payload: BackendEventPayload, request: Request, x_admin_token: str = Header(default="")) -> dict:
        _assert_admin(x_admin_token, settings, request)
        bot = getattr(app.state, "bot", None)
        if bot is None:
            raise HTTPException(status_code=503, detail="Telegram bot runtime is not configured")

        async with SessionFactory() as session:
            user = await resolve_target_user(
                session,
                user_id=payload.user_id,
                telegram_id=payload.telegram_id,
                seller_id=payload.seller_id,
            )
            if user is None:
                raise HTTPException(status_code=404, detail="User not found")

            event_payload = payload.model_dump()
            event_payload.update(payload.metadata or {})
            event_key = BackendEventFormatter.dedupe_key(event_payload)
            message = BackendEventFormatter.format(event_payload)
            receipt_repo = BackendEventReceiptRepository(session)
            if await receipt_repo.exists(str(user.id), event_key):
                return {
                    "ok": True,
                    "delivered": False,
                    "duplicate": True,
                    "event_key": event_key,
                    "event_type": payload.event_type,
                    "resolved_section": message.section,
                }

            services = build_services(session)
            delivery = await deliver_backend_notification(
                user=user,
                services=services,
                bot=bot,
                title=message.title,
                text=message.text,
                section=message.section,
            )
            connection = await MarketplaceConnectionRepository(session).get_by_user_id(str(user.id))
            await receipt_repo.record(
                user_id=str(user.id),
                connection_id=str(connection.id) if connection is not None else None,
                event_key=event_key,
                event_type=payload.event_type,
                section=message.section,
                payload=event_payload,
            )
            await session.commit()
            return {
                **delivery,
                "duplicate": False,
                "event_key": event_key,
                "event_type": payload.event_type,
                "resolved_section": message.section,
            }

    app.include_router(build_admin_router(settings))
    return app
