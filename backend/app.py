import logging
from datetime import datetime, timezone

from aiogram.types import Update
from fastapi import Depends, FastAPI, Header, HTTPException, Request

from bot.runtime import build_bot_runtime
from backend.routers.admin import build_admin_router
from shared.config import Settings, get_settings
from shared.logging import configure_logging


logger = logging.getLogger(__name__)


def _assert_admin(token: str, settings: Settings) -> None:
    if token == settings.admin_api_token and settings.admin_api_token:
        return
    if token in settings.admin_tokens:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def create_app(settings: Settings = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    bot, dispatcher = build_bot_runtime(settings)

    docs_url = "/docs" if settings.expose_api_docs else None
    redoc_url = "/redoc" if settings.expose_api_docs else None
    openapi_url = "/openapi.json" if settings.expose_api_docs else None
    app = FastAPI(title=settings.app_name, docs_url=docs_url, redoc_url=redoc_url, openapi_url=openapi_url)
    app.state.bot = bot
    app.state.dispatcher = dispatcher
    app.state.started_at = datetime.now(timezone.utc)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "uptime_seconds": int((datetime.now(timezone.utc) - app.state.started_at).total_seconds())}

    @app.get("/admin/health")
    async def admin_health(
        request: Request,
        x_admin_token: str = Header(default=""),
        app_settings: Settings = Depends(get_settings),
    ) -> dict:
        _assert_admin(x_admin_token, app_settings)
        if app_settings.admin_allowed_ips:
            client_ip = request.client.host if request.client else ""
            if client_ip not in app_settings.admin_allowed_ips:
                raise HTTPException(status_code=403, detail="Forbidden")
        return {
            "status": "ok",
            "service": app_settings.app_name,
            "uptime_seconds": int((datetime.now(timezone.utc) - app.state.started_at).total_seconds()),
        }

    @app.post(settings.telegram_webhook_path)
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str = Header(default=""),
    ) -> dict:
        if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=403, detail="Forbidden")
        payload = await request.json()
        update = Update.model_validate(payload, context={"bot": bot})
        await dispatcher.feed_update(bot, update)
        return {"ok": True}

    @app.on_event("startup")
    async def startup() -> None:
        if settings.telegram_uses_polling:
            logger.info("api_started_polling_mode")
        elif settings.telegram_webhook_url:
            await bot.set_webhook(url=settings.telegram_webhook_url, secret_token=settings.telegram_webhook_secret)
            logger.info("api_started_webhook_mode")
        else:
            logger.warning("api_started_without_webhook_url")

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await bot.session.close()
        logger.info("api_stopped")

    app.include_router(build_admin_router())
    return app
