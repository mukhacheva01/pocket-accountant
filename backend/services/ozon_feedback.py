"""Ozon feedback/reviews service.

Manages product reviews, ratings, and response automation.
"""

import logging

logger = logging.getLogger(__name__)


class OzonFeedbackService:
    def __init__(self, ozon_insights_repo) -> None:
        self._insights_repo = ozon_insights_repo

    async def get_summary(self, user_id: str) -> dict:
        """Get feedback summary for a user's products."""
        return await self._insights_repo.get_feedback_summary(user_id)

    async def get_unanswered(self, user_id: str) -> list[dict]:
        """Get list of unanswered reviews."""
        return []
