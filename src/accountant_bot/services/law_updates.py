from typing import Iterable, List

from accountant_bot.db.enums import LawUpdateReviewStatus
from accountant_bot.repositories.law_updates import LawUpdateRepository
from accountant_bot.services.profile_matching import ProfileContext


class LawUpdateService:
    def __init__(self, repository: LawUpdateRepository) -> None:
        self.repository = repository

    @staticmethod
    def is_relevant(update, profile: ProfileContext) -> bool:
        if update.review_status != LawUpdateReviewStatus.APPROVED:
            return False
        if update.affected_entity_types and profile.entity_type.value not in update.affected_entity_types:
            return False
        if update.affected_tax_regimes and profile.tax_regime.value not in update.affected_tax_regimes:
            return False
        if update.affected_marketplaces is not None and update.affected_marketplaces != profile.marketplaces_enabled:
            return False
        return True

    async def relevant_updates(self, profile: ProfileContext, min_importance: int) -> List:
        updates = await self.repository.list_approved(min_importance)
        return [item for item in updates if self.is_relevant(item, profile)]

    async def was_delivered(self, law_update_id: str, user_id: str) -> bool:
        return await self.repository.was_delivered(law_update_id, user_id)

    async def mark_delivered(self, law_update_id: str, user_id: str, delivered_at, status: str) -> None:
        await self.repository.mark_delivered(law_update_id, user_id, delivered_at, status)

    async def pending_review(self) -> List:
        return await self.repository.list_pending_review()
