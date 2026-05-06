from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.db.models import BusinessProfile, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def create_or_update_user(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: Optional[str],
        timezone: str,
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                timezone=timezone,
            )
            self.session.add(user)
            await self.session.flush()
            return user

        user.username = username
        user.first_name = first_name
        user.timezone = timezone
        await self.session.flush()
        return user


class BusinessProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: str) -> Optional[BusinessProfile]:
        result = await self.session.execute(
            select(BusinessProfile)
            .options(selectinload(BusinessProfile.user))
            .where(BusinessProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: str, payload: dict) -> BusinessProfile:
        profile = await self.get_by_user_id(user_id)
        if profile is None:
            profile = BusinessProfile(user_id=user_id, **payload)
            self.session.add(profile)
        else:
            for key, value in payload.items():
                setattr(profile, key, value)
        await self.session.flush()
        return profile
