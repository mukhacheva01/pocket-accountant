"""Ozon marketplace insights and analytics service.

Aggregates data from Ozon repos to provide business insights:
revenue trends, ad performance, content scores.
"""

import logging
from datetime import date

logger = logging.getLogger(__name__)


class OzonInsightsService:
    def __init__(self, ozon_data_repo, ozon_insights_repo) -> None:
        self._data_repo = ozon_data_repo
        self._insights_repo = ozon_insights_repo

    async def revenue_summary(self, user_id: str, since: date, until: date) -> dict:
        """Get revenue summary for a date range."""
        return await self._data_repo.get_revenue(user_id, since, until)

    async def ad_performance(self, user_id: str, since: date, until: date) -> dict:
        """Get advertising performance summary."""
        return await self._insights_repo.get_ad_summary(user_id, since, until)

    async def dashboard(self, user_id: str) -> dict:
        """Get full Ozon dashboard data."""
        product_count = await self._data_repo.get_product_count(user_id)
        content_score = await self._insights_repo.get_content_score(user_id)
        feedback = await self._insights_repo.get_feedback_summary(user_id)
        return {
            "products": product_count,
            "content_score": content_score["average_score"],
            "reviews": feedback["total_reviews"],
            "avg_rating": feedback["average_rating"],
        }
