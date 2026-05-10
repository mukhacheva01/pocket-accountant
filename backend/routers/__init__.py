from fastapi import APIRouter

from backend.routers.health import router as health_router
from backend.routers.users import router as users_router
from backend.routers.events import router as events_router
from backend.routers.finance import router as finance_router
from backend.routers.ai import router as ai_router
from backend.routers.subscription import router as subscription_router
from backend.routers.tax import router as tax_router
from backend.routers.bot_gateway import router as bot_gateway_router
from backend.routers.admin import build_admin_router


def build_api_router() -> APIRouter:
    api = APIRouter(prefix="/api")
    api.include_router(health_router)
    api.include_router(users_router)
    api.include_router(events_router)
    api.include_router(finance_router)
    api.include_router(ai_router)
    api.include_router(subscription_router)
    api.include_router(tax_router)
    api.include_router(bot_gateway_router)
    api.include_router(build_admin_router())
    return api
