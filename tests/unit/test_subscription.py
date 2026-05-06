"""Tests for backend.services.subscription."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from shared.config import Settings
from shared.db.enums import SubscriptionPlan
from backend.services.subscription import PLAN_DETAILS, SubscriptionService


def _make_settings(**overrides) -> Settings:
    base = {"DATABASE_URL": "sqlite+aiosqlite:///test.db", "REDIS_URL": "redis://localhost:6379/0"}
    base.update(overrides)
    return Settings(**base)


def _user(telegram_id=12345, ai_today=0, ai_date=None, bonus=0):
    return SimpleNamespace(
        telegram_id=telegram_id,
        ai_requests_today=ai_today,
        ai_requests_date=ai_date,
        referral_bonus_requests=bonus,
    )


def _sub(plan=SubscriptionPlan.BASIC, expires_at=None, ai_limit=50):
    return SimpleNamespace(plan=plan, expires_at=expires_at, ai_requests_limit=ai_limit)


@pytest.fixture()
def service():
    settings = _make_settings(
        TESTER_TELEGRAM_IDS="999",
        STARS_PRICE_BASIC=150,
        STARS_PRICE_PRO=400,
        STARS_PRICE_ANNUAL=3500,
        FREE_AI_REQUESTS_PER_DAY=3,
    )
    repo = AsyncMock()
    users = AsyncMock()
    return SubscriptionService(repo, users, settings)


class TestIsTester:
    def test_tester_detected(self, service):
        assert service.is_tester(_user(telegram_id=999)) is True

    def test_non_tester(self, service):
        assert service.is_tester(_user(telegram_id=111)) is False


class TestGetPrice:
    def test_basic_price(self, service):
        assert service.get_price(SubscriptionPlan.BASIC) == 150

    def test_pro_price(self, service):
        assert service.get_price(SubscriptionPlan.PRO) == 400

    def test_annual_price(self, service):
        assert service.get_price(SubscriptionPlan.ANNUAL) == 3500

    def test_free_price(self, service):
        assert service.get_price(SubscriptionPlan.FREE) == 0


class TestIsActive:
    def test_none_sub(self, service):
        assert service.is_active(None) is False

    def test_free_plan(self, service):
        sub = _sub(plan=SubscriptionPlan.FREE, expires_at=datetime.now(timezone.utc) + timedelta(days=30))
        assert service.is_active(sub) is False

    def test_expired(self, service):
        sub = _sub(expires_at=datetime.now(timezone.utc) - timedelta(days=1))
        assert service.is_active(sub) is False

    def test_active(self, service):
        sub = _sub(expires_at=datetime.now(timezone.utc) + timedelta(days=30))
        assert service.is_active(sub) is True

    def test_no_expiry(self, service):
        sub = _sub(expires_at=None)
        assert service.is_active(sub) is False


class TestCanUseAI:
    async def test_tester_unlimited(self, service):
        ok, remaining = await service.can_use_ai(_user(telegram_id=999), None)
        assert ok is True
        assert remaining == 10_000

    async def test_active_sub(self, service):
        sub = _sub(expires_at=datetime.now(timezone.utc) + timedelta(days=30), ai_limit=50)
        ok, remaining = await service.can_use_ai(_user(), sub)
        assert ok is True
        assert remaining == 50

    async def test_free_tier_fresh_day(self, service):
        ok, remaining = await service.can_use_ai(_user(), None)
        assert ok is True
        assert remaining == 3

    async def test_free_tier_exhausted(self, service):
        from datetime import date
        ok, remaining = await service.can_use_ai(
            _user(ai_today=3, ai_date=date.today()), None
        )
        assert ok is False
        assert remaining == 0

    async def test_free_tier_with_bonus(self, service):
        from datetime import date
        ok, remaining = await service.can_use_ai(
            _user(ai_today=3, ai_date=date.today(), bonus=2), None
        )
        assert ok is True
        assert remaining == 2


class TestIncrementAIUsage:
    async def test_increments_counter(self, service):
        user = _user()
        user.ai_requests_today = 0
        user.ai_requests_date = None
        await service.increment_ai_usage(user)
        assert user.ai_requests_today == 1

    async def test_skips_tester(self, service):
        user = _user(telegram_id=999)
        user.ai_requests_today = 0
        await service.increment_ai_usage(user)
        assert user.ai_requests_today == 0

    async def test_resets_on_new_day(self, service):
        from datetime import date, timedelta as td
        user = _user()
        user.ai_requests_today = 5
        user.ai_requests_date = date.today() - td(days=1)
        await service.increment_ai_usage(user)
        assert user.ai_requests_today == 1
        assert user.ai_requests_date == date.today()


class TestPlanDetails:
    def test_basic_plan_details(self):
        assert PLAN_DETAILS[SubscriptionPlan.BASIC]["days"] == 30
        assert PLAN_DETAILS[SubscriptionPlan.BASIC]["ai_limit"] == 50

    def test_pro_plan_details(self):
        assert PLAN_DETAILS[SubscriptionPlan.PRO]["days"] == 30
        assert PLAN_DETAILS[SubscriptionPlan.PRO]["ai_limit"] == 999

    def test_annual_plan_details(self):
        assert PLAN_DETAILS[SubscriptionPlan.ANNUAL]["days"] == 365
