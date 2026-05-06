from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accountant_bot.db.models import Payment, Subscription


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: str) -> Optional[Subscription]:
        result = await self.session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: str, payload: dict) -> Subscription:
        sub = await self.get_by_user_id(user_id)
        if sub is None:
            sub = Subscription(user_id=user_id, **payload)
            self.session.add(sub)
        else:
            for key, value in payload.items():
                setattr(sub, key, value)
        await self.session.flush()
        return sub

    async def add_payment(self, payment: Payment) -> Payment:
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def payment_exists(self, telegram_payment_id: str) -> bool:
        if not telegram_payment_id:
            return False
        result = await self.session.execute(
            select(Payment).where(Payment.telegram_payment_id == telegram_payment_id)
        )
        return result.scalar_one_or_none() is not None
