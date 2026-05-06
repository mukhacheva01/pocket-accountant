"""Extended tests for backend.services.subscription.SubscriptionService."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from shared.db.enums import PaymentStatus, SubscriptionPlan
from shared.db.models import Subscription, User
from backend.services.subscription import SubscriptionService, PLAN_DETAILS


def _make_service():
    repo = AsyncMock()
    users = AsyncMock()
    settings = MagicMock()
    settings.tester_telegram_ids = {999}
    settings.stars_price_basic = 100
    settings.stars_price_pro = 250
    settings.stars_price_annual = 2000
    settings.free_ai_requests_per_day = 3
    return SubscriptionService(repo, users, settings)


class TestSubscriptionService:
    def test_is_tester(self):
        svc = _make_service()
        user = MagicMock()
        user.telegram_id = 999
        assert svc.is_tester(user) is True
        user.telegram_id = 111
        assert svc.is_tester(user) is False

    def test_get_price(self):
        svc = _make_service()
        assert svc.get_price(SubscriptionPlan.BASIC) == 100
        assert svc.get_price(SubscriptionPlan.PRO) == 250
        assert svc.get_price(SubscriptionPlan.ANNUAL) == 2000
        assert svc.get_price(SubscriptionPlan.FREE) == 0

    def test_is_active_none(self):
        svc = _make_service()
        assert svc.is_active(None) is False

    def test_is_active_free(self):
        svc = _make_service()
        sub = MagicMock()
        sub.plan = SubscriptionPlan.FREE
        assert svc.is_active(sub) is False

    def test_is_active_expired(self):
        svc = _make_service()
        sub = MagicMock()
        sub.plan = SubscriptionPlan.BASIC
        sub.expires_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        assert svc.is_active(sub) is False

    def test_is_active_valid(self):
        svc = _make_service()
        sub = MagicMock()
        sub.plan = SubscriptionPlan.BASIC
        sub.expires_at = datetime(2099, 1, 1, tzinfo=timezone.utc)
        assert svc.is_active(sub) is True

    def test_is_active_no_expiry(self):
        svc = _make_service()
        sub = MagicMock()
        sub.plan = SubscriptionPlan.BASIC
        sub.expires_at = None
        assert svc.is_active(sub) is False

    async def test_activate(self):
        svc = _make_service()
        svc.repo.upsert = AsyncMock(return_value=MagicMock())
        result = await svc.activate("u1", SubscriptionPlan.BASIC)
        svc.repo.upsert.assert_awaited_once()

    async def test_cancel(self):
        svc = _make_service()
        svc.repo.upsert = AsyncMock(return_value=MagicMock())
        result = await svc.cancel("u1")
        call_args = svc.repo.upsert.call_args
        assert call_args[0][1]["plan"] == SubscriptionPlan.FREE

    async def test_grant(self):
        svc = _make_service()
        svc.repo.upsert = AsyncMock(return_value=MagicMock())
        result = await svc.grant("u1", SubscriptionPlan.PRO, 14)
        call_args = svc.repo.upsert.call_args
        assert call_args[0][1]["plan"] == SubscriptionPlan.PRO

    async def test_record_payment(self):
        svc = _make_service()
        svc.repo.add_payment = AsyncMock(return_value=MagicMock())
        result = await svc.record_payment("u1", SubscriptionPlan.BASIC, 100, "tg_123")
        svc.repo.add_payment.assert_awaited_once()

    async def test_payment_exists(self):
        svc = _make_service()
        svc.repo.payment_exists = AsyncMock(return_value=True)
        assert await svc.payment_exists("tg_123") is True

    async def test_can_use_ai_tester(self):
        svc = _make_service()
        user = MagicMock()
        user.telegram_id = 999
        can, remaining = await svc.can_use_ai(user, None)
        assert can is True
        assert remaining == 10_000

    async def test_can_use_ai_active_sub(self):
        svc = _make_service()
        user = MagicMock()
        user.telegram_id = 111
        sub = MagicMock()
        sub.plan = SubscriptionPlan.PRO
        sub.expires_at = datetime(2099, 1, 1, tzinfo=timezone.utc)
        sub.ai_requests_limit = 999
        can, remaining = await svc.can_use_ai(user, sub)
        assert can is True
        assert remaining == 999

    async def test_can_use_ai_free_fresh_day(self):
        svc = _make_service()
        user = MagicMock()
        user.telegram_id = 111
        user.ai_requests_date = None
        user.ai_requests_today = 0
        user.referral_bonus_requests = 0
        can, remaining = await svc.can_use_ai(user, None)
        assert can is True
        assert remaining == 3

    async def test_can_use_ai_free_exhausted(self):
        svc = _make_service()
        user = MagicMock()
        user.telegram_id = 111
        user.ai_requests_date = date.today()
        user.ai_requests_today = 3
        user.referral_bonus_requests = 0
        can, remaining = await svc.can_use_ai(user, None)
        assert can is False
        assert remaining == 0

    async def test_increment_ai_usage_tester(self):
        svc = _make_service()
        user = MagicMock()
        user.telegram_id = 999
        await svc.increment_ai_usage(user)

    async def test_increment_ai_usage_new_day(self):
        svc = _make_service()
        user = MagicMock()
        user.telegram_id = 111
        user.ai_requests_date = None
        await svc.increment_ai_usage(user)
        assert user.ai_requests_today == 1

    async def test_increment_ai_usage_same_day(self):
        svc = _make_service()
        user = MagicMock()
        user.telegram_id = 111
        user.ai_requests_date = date.today()
        user.ai_requests_today = 2
        await svc.increment_ai_usage(user)
        assert user.ai_requests_today == 3
