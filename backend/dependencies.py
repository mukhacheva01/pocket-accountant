"""FastAPI dependency injection helpers."""

from __future__ import annotations



from shared.config import Settings, get_settings
from shared.db.session import SessionFactory
from backend.services.container import build_services


async def get_services_dep():
    async with SessionFactory() as session:
        yield build_services(session)


def get_settings_dep() -> Settings:
    return get_settings()
