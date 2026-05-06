from datetime import timedelta
from typing import Optional

from shared.clock import utcnow
from shared.config import Settings
from shared.db.enums import PaymentStatus, SubscriptionPlan
from shared.db.models import Payment, Subscription, User
from backend.repositories.subscriptions import SubscriptionRepository
from backend.repositories.users import UserRepository


PLAN_DETAILS = {
    SubscriptionPlan.BASIC: {"label": "Базовый", "days": 30, "ai_limit": 50},
    SubscriptionPlan.PRO: {"label": "Про", "days": 30, "ai_limit": 999},
    SubscriptionPlan.ANNUAL: {"label": "Годовой", "days": 365, "ai_limit": 999},
}


class SubscriptionService:
    def __init__(self, repo: SubscriptionRepository, users: UserRepository, settings: Settings) -> None:
        self.repo = repo
        self.users = users
        self.settings = settings

    def is_tester(self, user: User) -> bool:
        return user.telegram_id in self.settings.tester_telegram_ids

    def get_price(self, plan: SubscriptionPlan) -> int:
        prices = {
            SubscriptionPlan.BASIC: self.settings.stars_price_basic,
            SubscriptionPlan.PRO: self.settings.stars_price_pro,
            SubscriptionPlan.ANNUAL: self.settings.stars_price_annual,
        }
        return prices.get(plan, 0)

    async def get_subscription(self, user_id: str) -> Optional[Subscription]:
        return await self.repo.get_by_user_id(user_id)

    def is_active(self, sub: Optional[Subscription]) -> bool:
        if sub is None or sub.plan == SubscriptionPlan.FREE:
            return False
        if sub.expires_at is None:
            return False
        return sub.expires_at > utcnow()

    async def activate(self, user_id: str, plan: SubscriptionPlan) -> Subscription:
        details = PLAN_DETAILS[plan]
        now = utcnow()
        return await self.repo.upsert(user_id, {
            "plan": plan,
            "started_at": now,
            "expires_at": now + timedelta(days=details["days"]),
            "auto_renew": True,
            "ai_requests_limit": details["ai_limit"],
        })

    async def cancel(self, user_id: str) -> Subscription:
        now = utcnow()
        return await self.repo.upsert(user_id, {
            "plan": SubscriptionPlan.FREE,
            "started_at": None,
            "expires_at": now,
            "auto_renew": False,
            "ai_requests_limit": 0,
        })

    async def grant(self, user_id: str, plan: SubscriptionPlan, days: int) -> Subscription:
        now = utcnow()
        return await self.repo.upsert(user_id, {
            "plan": plan,
            "started_at": now,
            "expires_at": now + timedelta(days=days),
            "auto_renew": False,
            "ai_requests_limit": PLAN_DETAILS[plan]["ai_limit"],
        })

    async def record_payment(self, user_id: str, plan: SubscriptionPlan, stars: int, telegram_payment_id: str) -> Payment:
        payment = Payment(
            user_id=user_id,
            amount_stars=stars,
            plan=plan,
            status=PaymentStatus.COMPLETED,
            telegram_payment_id=telegram_payment_id,
        )
        return await self.repo.add_payment(payment)

    async def payment_exists(self, telegram_payment_id: str) -> bool:
        return await self.repo.payment_exists(telegram_payment_id)

    async def can_use_ai(self, user: User, sub: Optional[Subscription]) -> tuple[bool, int]:
        """Returns (can_use, remaining_requests)."""
        if self.is_tester(user):
            return True, 10_000
        if self.is_active(sub):
            return True, sub.ai_requests_limit

        # Free tier: daily limit
        from datetime import date
        today = date.today()
        daily_limit = self.settings.free_ai_requests_per_day

        if user.ai_requests_date is None or user.ai_requests_date != today:
            remaining = daily_limit + user.referral_bonus_requests
        else:
            remaining = max(0, daily_limit + user.referral_bonus_requests - user.ai_requests_today)

        return remaining > 0, remaining

    async def increment_ai_usage(self, user: User) -> None:
        if self.is_tester(user):
            return
        from datetime import date
        today = date.today()
        if user.ai_requests_date is None or user.ai_requests_date != today:
            user.ai_requests_today = 1
            user.ai_requests_date = today
        else:
            user.ai_requests_today += 1
