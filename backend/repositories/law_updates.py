from typing import List

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.enums import LawUpdateReviewStatus
from shared.db.models import LawUpdate, LawUpdateDelivery


class LawUpdateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_pending_review(self) -> List[LawUpdate]:
        result = await self.session.execute(
            select(LawUpdate).where(LawUpdate.review_status == LawUpdateReviewStatus.UNREVIEWED)
        )
        return list(result.scalars().all())

    async def list_approved(self, min_importance: int) -> List[LawUpdate]:
        result = await self.session.execute(
            select(LawUpdate)
            .where(
                and_(
                    LawUpdate.review_status == LawUpdateReviewStatus.APPROVED,
                    LawUpdate.is_active.is_(True),
                    LawUpdate.importance_score >= min_importance,
                )
            )
            .order_by(desc(LawUpdate.published_at))
        )
        return list(result.scalars().all())

    async def was_delivered(self, law_update_id: str, user_id: str) -> bool:
        result = await self.session.execute(
            select(LawUpdateDelivery).where(
                and_(
                    LawUpdateDelivery.law_update_id == law_update_id,
                    LawUpdateDelivery.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def mark_delivered(self, law_update_id: str, user_id: str, delivered_at, status: str) -> None:
        result = await self.session.execute(
            select(LawUpdateDelivery).where(
                and_(
                    LawUpdateDelivery.law_update_id == law_update_id,
                    LawUpdateDelivery.user_id == user_id,
                )
            )
        )
        delivery = result.scalar_one_or_none()
        if delivery is None:
            delivery = LawUpdateDelivery(
                law_update_id=law_update_id,
                user_id=user_id,
                delivered_at=delivered_at,
                status=status,
            )
            self.session.add(delivery)
        else:
            delivery.delivered_at = delivered_at
            delivery.status = status
        await self.session.flush()
