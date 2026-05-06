from dataclasses import dataclass
from typing import Dict, Optional

from accountant_bot.db.enums import EntityType, TaxRegime
from accountant_bot.repositories.users import BusinessProfileRepository, UserRepository


@dataclass
class OnboardingDraft:
    entity_type: EntityType
    tax_regime: TaxRegime
    has_employees: bool
    marketplaces_enabled: bool
    industry: Optional[str]
    region: str
    timezone: str
    reminder_settings: Dict[str, object]


class OnboardingService:
    def __init__(self, users: UserRepository, profiles: BusinessProfileRepository) -> None:
        self.users = users
        self.profiles = profiles

    async def ensure_user(self, telegram_id: int, username: Optional[str], first_name: Optional[str], timezone: str):
        return await self.users.create_or_update_user(telegram_id, username, first_name, timezone)

    async def load_profile(self, user_id: str):
        return await self.profiles.get_by_user_id(user_id)

    async def save_profile(self, user_id: str, draft: OnboardingDraft):
        return await self.profiles.upsert(
            user_id,
            {
                "entity_type": draft.entity_type,
                "tax_regime": draft.tax_regime,
                "has_employees": draft.has_employees,
                "marketplaces_enabled": draft.marketplaces_enabled,
                "industry": draft.industry,
                "region": draft.region,
                "reminder_settings": draft.reminder_settings,
            },
        )
