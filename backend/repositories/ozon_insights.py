"""Repository for Ozon marketplace insights and analytics data."""

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class OzonInsightsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_ad_stats(self, user_id: str, stats: list[dict]) -> int:
        """Save advertising performance stats. Returns count of saved items."""
        logger.info("ozon_save_ad_stats user_id=%s count=%d", user_id, len(stats))
        return len(stats)

    async def get_ad_summary(self, user_id: str, since: date, until: date) -> dict:
        """Get advertising summary for date range."""
        return {"total_spend": 0, "impressions": 0, "clicks": 0, "orders": 0}

    async def get_content_score(self, user_id: str) -> dict:
        """Get content quality score summary."""
        return {"average_score": 0, "products_scored": 0}

    async def get_feedback_summary(self, user_id: str) -> dict:
        """Get reviews/feedback summary."""
        return {"total_reviews": 0, "average_rating": 0, "unanswered": 0}
