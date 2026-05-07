"""Tests for backend.services.calendar."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from shared.db.enums import EntityType, TaxRegime
from backend.services.calendar import CalendarService
from backend.services.profile_matching import ProfileContext


@pytest.fixture()
def svc():
    repo = AsyncMock()
    return CalendarService(repo)


def _profile(**overrides) -> ProfileContext:
    defaults = {
        "entity_type": EntityType.INDIVIDUAL_ENTREPRENEUR,
        "tax_regime": TaxRegime.USN_INCOME,
        "has_employees": False,
        "marketplaces_enabled": False,
        "region": "Moscow",
    }
    defaults.update(overrides)
    return ProfileContext(**defaults)


class TestSyncUserEvents:
    async def test_filters_templates(self, svc):
        t1 = SimpleNamespace(
            applies_to_entity_types=["ip"],
            applies_to_tax_regimes=[],
            applies_if_has_employees=None,
            applies_if_marketplaces=None,
            applies_to_regions=[],
            due_date=date(2026, 7, 15),
        )
        t2 = SimpleNamespace(
            applies_to_entity_types=["ooo"],
            applies_to_tax_regimes=[],
            applies_if_has_employees=None,
            applies_if_marketplaces=None,
            applies_to_regions=[],
            due_date=date(2026, 7, 15),
        )
        svc.calendar_repo.list_active_templates.return_value = [t1, t2]
        count = await svc.sync_user_events("u1", _profile())
        assert count == 1
        svc.calendar_repo.upsert_user_event.assert_awaited_once()

    async def test_no_templates(self, svc):
        svc.calendar_repo.list_active_templates.return_value = []
        count = await svc.sync_user_events("u1", _profile())
        assert count == 0


class TestUpcoming:
    async def test_delegates(self, svc):
        svc.calendar_repo.list_upcoming_for_user.return_value = ["e1", "e2"]
        result = await svc.upcoming("u1", days=14)
        assert result == ["e1", "e2"]


class TestOverdue:
    async def test_delegates(self, svc):
        svc.calendar_repo.list_upcoming_for_user.return_value = []
        result = await svc.overdue("u1")
        assert result == []
