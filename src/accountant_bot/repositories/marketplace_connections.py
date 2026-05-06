from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from accountant_bot.db.models import MarketplaceConnection


class MarketplaceConnectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: str) -> Optional[MarketplaceConnection]:
        result = await self.session.execute(
            select(MarketplaceConnection).where(MarketplaceConnection.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: str, payload: dict) -> MarketplaceConnection:
        connection = await self.get_by_user_id(user_id)
        if connection is None:
            connection = MarketplaceConnection(user_id=user_id, **payload)
            self.session.add(connection)
        else:
            for key, value in payload.items():
                setattr(connection, key, value)
        await self.session.flush()
        return connection
