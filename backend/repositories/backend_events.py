"""Repository for backend-generated events (audit log, sync events, etc.)."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BackendEventsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_event(
        self, event_type: str, user_id: str | None = None, payload: dict | None = None,
    ) -> None:
        """Log a backend event (sync completion, error, admin action, etc.)."""
        logger.info(
            "backend_event type=%s user_id=%s payload=%s",
            event_type, user_id, payload,
        )

    async def get_recent(self, limit: int = 50) -> list[dict]:
        """Get recent backend events."""
        return []

    async def get_by_user(self, user_id: str, limit: int = 50) -> list[dict]:
        """Get events for a specific user."""
        return []
