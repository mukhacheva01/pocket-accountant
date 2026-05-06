"""Extended tests for backend.services.law_updates.LawUpdateService."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from shared.db.enums import EntityType, LawUpdateReviewStatus, TaxRegime
from backend.services.law_updates import LawUpdateService
from backend.services.profile_matching import ProfileContext


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


@pytest.fixture()
def svc():
    repo = AsyncMock()
    return LawUpdateService(repo)


class TestRelevantUpdates:
    async def test_filters_and_returns(self, svc):
        u1 = SimpleNamespace(
            review_status=LawUpdateReviewStatus.APPROVED,
            affected_entity_types=None,
            affected_tax_regimes=None,
            affected_marketplaces=None,
            importance_score=8,
        )
        u2 = SimpleNamespace(
            review_status=LawUpdateReviewStatus.REJECTED,
            affected_entity_types=None,
            affected_tax_regimes=None,
            affected_marketplaces=None,
            importance_score=5,
        )
        svc.repository.list_approved.return_value = [u1, u2]
        result = await svc.relevant_updates(_profile(), min_importance=3)
        assert len(result) == 1
        assert result[0] is u1


class TestWasDelivered:
    async def test_delegates(self, svc):
        svc.repository.was_delivered.return_value = True
        result = await svc.was_delivered("lu1", "u1")
        assert result is True
        svc.repository.was_delivered.assert_awaited_once_with("lu1", "u1")


class TestMarkDelivered:
    async def test_delegates(self, svc):
        from datetime import datetime, timezone
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        await svc.mark_delivered("lu1", "u1", now, "sent")
        svc.repository.mark_delivered.assert_awaited_once()


class TestPendingReview:
    async def test_delegates(self, svc):
        svc.repository.list_pending_review.return_value = []
        result = await svc.pending_review()
        assert result == []
