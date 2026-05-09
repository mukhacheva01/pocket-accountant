"""Ozon content quality analysis service.

Analyzes product card quality (titles, descriptions, images)
and provides improvement recommendations.
"""

import logging

logger = logging.getLogger(__name__)


class OzonContentService:
    def __init__(self, ozon_data_repo, ozon_insights_repo) -> None:
        self._data_repo = ozon_data_repo
        self._insights_repo = ozon_insights_repo

    async def analyze_content(self, user_id: str) -> dict:
        """Analyze content quality for user's products."""
        score = await self._insights_repo.get_content_score(user_id)
        return {
            "average_score": score["average_score"],
            "products_scored": score["products_scored"],
            "recommendations": [],
        }
