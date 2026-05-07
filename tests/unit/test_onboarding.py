"""Tests for backend.services.onboarding."""

from unittest.mock import AsyncMock

import pytest

from shared.db.enums import EntityType, TaxRegime
from backend.services.onboarding import OnboardingDraft, OnboardingService


@pytest.fixture()
def service():
    users = AsyncMock()
    profiles = AsyncMock()
    return OnboardingService(users, profiles)


class TestOnboardingService:
    async def test_ensure_user_delegates(self, service):
        service.users.create_or_update_user.return_value = "user_obj"
        result = await service.ensure_user(123, "nick", "Name", "Europe/Moscow")
        service.users.create_or_update_user.assert_awaited_once_with(123, "nick", "Name", "Europe/Moscow")
        assert result == "user_obj"

    async def test_load_profile_delegates(self, service):
        service.profiles.get_by_user_id.return_value = "profile"
        result = await service.load_profile("uid")
        service.profiles.get_by_user_id.assert_awaited_once_with("uid")
        assert result == "profile"

    async def test_save_profile_delegates(self, service):
        draft = OnboardingDraft(
            entity_type=EntityType.INDIVIDUAL_ENTREPRENEUR,
            tax_regime=TaxRegime.USN_INCOME,
            has_employees=False,
            marketplaces_enabled=True,
            industry="IT",
            region="Moscow",
            timezone="Europe/Moscow",
            reminder_settings={"notify_taxes": True},
        )
        await service.save_profile("uid", draft)
        service.profiles.upsert.assert_awaited_once()
        call_args = service.profiles.upsert.call_args
        assert call_args[0][0] == "uid"
        data = call_args[0][1]
        assert data["entity_type"] == EntityType.INDIVIDUAL_ENTREPRENEUR
        assert data["tax_regime"] == TaxRegime.USN_INCOME
        assert data["marketplaces_enabled"] is True
        assert data["industry"] == "IT"


class TestOnboardingDraft:
    def test_creation(self):
        draft = OnboardingDraft(
            entity_type=EntityType.SELF_EMPLOYED,
            tax_regime=TaxRegime.NPD,
            has_employees=False,
            marketplaces_enabled=False,
            industry=None,
            region="SPB",
            timezone="Europe/Moscow",
            reminder_settings={},
        )
        assert draft.entity_type == EntityType.SELF_EMPLOYED
        assert draft.region == "SPB"
