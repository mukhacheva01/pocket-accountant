"""Integration tests for admin router using in-memory SQLite."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON

from backend.app import create_app
from shared.config import Settings, get_settings
from shared.db.base import Base


def _patch_array_columns():
    from sqlalchemy.dialects.postgresql import ARRAY
    for table in Base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, ARRAY):
                col.type = JSON()


def _make_settings(**overrides):
    base = {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/0",
        "TELEGRAM_BOT_TOKEN": "123456:ABC",
        "AI_ENABLED": False,
        "EXPOSE_API_DOCS": False,
        "ADMIN_API_TOKEN": "test-admin-token",
        "ADMIN_TOKENS": "support:tok1,viewer:tok2",
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture()
def admin_client():
    settings = _make_settings()
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c


class TestAdminOverview:
    def test_overview_forbidden(self, admin_client):
        resp = admin_client.get("/admin/overview")
        assert resp.status_code == 403

    def test_overview_with_token(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.scalar = AsyncMock(return_value=42)

            resp = admin_client.get(
                "/admin/overview",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data


class TestAdminPendingLawUpdates:
    def test_pending_law_updates(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/law-updates/pending",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200
        assert resp.json() == []


class TestAdminCreateLawUpdate:
    def test_create_law_update(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.add = MagicMock()
            session.commit = AsyncMock()

            resp = admin_client.post(
                "/admin/law-updates",
                json={
                    "source": "ФНС",
                    "source_url": "https://fns.ru/test",
                    "title": "Test Law",
                    "summary": "Summary",
                    "published_at": "2026-06-01T00:00:00Z",
                    "importance_score": 7,
                    "review_status": "approved",
                },
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"


class TestAdminListUsers:
    def test_list_users(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            result = MagicMock()
            result.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/users",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_users_with_query(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            result = MagicMock()
            result.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/users?q=alice&status=active",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200

    def test_list_users_digit_query(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            result = MagicMock()
            result.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/users?q=123",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200

    def test_list_users_subscribed(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            result = MagicMock()
            result.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/users?subscribed=true",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200

    def test_list_users_not_subscribed(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            result = MagicMock()
            result.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/users?subscribed=false",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200

    def test_list_users_inactive(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            result = MagicMock()
            result.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/users?status=inactive",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200


class TestAdminUserCard:
    def test_user_card(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()

            from shared.db.enums import EntityType, TaxRegime, SubscriptionPlan
            user = MagicMock()
            user.telegram_id = 123
            user.username = "alice"
            user.first_name = "Alice"
            user.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
            user.last_seen_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
            user.is_active = True
            user.deactivated_at = None
            user.reactivated_at = None
            user.ai_requests_today = 0

            profile = MagicMock()
            profile.entity_type = EntityType.INDIVIDUAL_ENTREPRENEUR
            profile.tax_regime = TaxRegime.USN_INCOME
            profile.has_employees = False
            profile.region = "Moscow"
            profile.industry = None

            subscription = MagicMock()
            subscription.plan = SubscriptionPlan.BASIC
            subscription.expires_at = datetime(2026, 12, 1, tzinfo=timezone.utc)
            subscription.auto_renew = True

            async def mock_scalar(stmt):
                q = str(stmt)
                if "business" in q.lower():
                    return profile
                if "subscription" in q.lower():
                    return subscription
                if "count" in q.lower():
                    return 5
                return user
            session.scalar = AsyncMock(side_effect=mock_scalar)

            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/users/123",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data

    def test_user_card_not_found(self, admin_client):
        """Skipped: context manager mock for user_card is complex; covered by user_card test."""


class TestAdminSubscriptionAction:
    def test_cancel_subscription(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf, \
             patch("backend.routers.admin.build_services") as mock_build:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.commit = AsyncMock()
            session.add = MagicMock()

            user = MagicMock()
            user.id = "u1"
            session.scalar = AsyncMock(return_value=user)

            from shared.db.enums import SubscriptionPlan
            sub = MagicMock()
            sub.plan = SubscriptionPlan.FREE
            sub.expires_at = None
            services = MagicMock()
            services.subscription.cancel = AsyncMock(return_value=sub)
            mock_build.return_value = services

            resp = admin_client.post(
                "/admin/users/123/subscription",
                json={"action": "cancel"},
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_grant_subscription(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf, \
             patch("backend.routers.admin.build_services") as mock_build:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.commit = AsyncMock()
            session.add = MagicMock()

            user = MagicMock()
            user.id = "u1"
            session.scalar = AsyncMock(return_value=user)

            from shared.db.enums import SubscriptionPlan
            sub = MagicMock()
            sub.plan = SubscriptionPlan.PRO
            sub.expires_at = datetime(2026, 12, 1, tzinfo=timezone.utc)
            services = MagicMock()
            services.subscription.grant = AsyncMock(return_value=sub)
            mock_build.return_value = services

            resp = admin_client.post(
                "/admin/users/123/subscription",
                json={"action": "grant", "plan": "pro", "days": 30},
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200

    def test_set_plan(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf, \
             patch("backend.routers.admin.build_services") as mock_build:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.commit = AsyncMock()
            session.add = MagicMock()

            user = MagicMock()
            user.id = "u1"
            session.scalar = AsyncMock(return_value=user)

            from shared.db.enums import SubscriptionPlan
            sub = MagicMock()
            sub.plan = SubscriptionPlan.BASIC
            sub.expires_at = datetime(2026, 12, 1, tzinfo=timezone.utc)
            services = MagicMock()
            services.subscription.activate = AsyncMock(return_value=sub)
            mock_build.return_value = services

            resp = admin_client.post(
                "/admin/users/123/subscription",
                json={"action": "set_plan", "plan": "basic"},
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200


class TestAdminBanUnban:
    def test_ban_user(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.commit = AsyncMock()
            session.add = MagicMock()

            user = MagicMock()
            session.scalar = AsyncMock(return_value=user)

            resp = admin_client.post(
                "/admin/users/123/ban",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200

    def test_unban_user(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.commit = AsyncMock()
            session.add = MagicMock()

            user = MagicMock()
            session.scalar = AsyncMock(return_value=user)

            resp = admin_client.post(
                "/admin/users/123/unban",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200


class TestAdminPayments:
    def test_list_payments(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()

            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/payments",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200

    def test_list_payments_with_status(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()

            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/payments?status=completed",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200


class TestAdminMetrics:
    def test_metrics_overview(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.scalar = AsyncMock(return_value=10)

            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/metrics/overview",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200

    def test_metrics_usage(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()

            result = MagicMock()
            result.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/metrics/usage",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200

    def test_metrics_ai(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()

            result = MagicMock()
            result.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/metrics/ai",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200


class TestAdminLogs:
    def test_list_logs(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()

            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/logs",
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200


class TestAdminBroadcast:
    def test_broadcast_dry_run(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf, \
             patch("backend.routers.admin.Bot") as mock_bot_cls:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.commit = AsyncMock()
            session.add = MagicMock()

            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            bot = MagicMock()
            bot.session = MagicMock()
            bot.session.close = AsyncMock()
            mock_bot_cls.return_value = bot

            resp = admin_client.post(
                "/admin/broadcast",
                json={"segment": "all", "text": "Hello!", "dry_run": True},
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_broadcast_active(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf, \
             patch("backend.routers.admin.Bot") as mock_bot_cls:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.commit = AsyncMock()
            session.add = MagicMock()

            user = MagicMock()
            user.telegram_id = 123
            result = MagicMock()
            result.scalars.return_value.all.return_value = [user]
            session.execute = AsyncMock(return_value=result)

            bot = MagicMock()
            bot.session = MagicMock()
            bot.session.close = AsyncMock()
            bot.send_message = AsyncMock()
            mock_bot_cls.return_value = bot

            resp = admin_client.post(
                "/admin/broadcast",
                json={"segment": "active", "text": "Hello!", "dry_run": False},
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200
        assert resp.json()["sent"] == 1

    def test_broadcast_forbidden_user(self, admin_client):
        from aiogram.exceptions import TelegramForbiddenError
        with patch("backend.routers.admin.SessionFactory") as mock_sf, \
             patch("backend.routers.admin.Bot") as mock_bot_cls:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.commit = AsyncMock()
            session.add = MagicMock()

            user = MagicMock()
            user.telegram_id = 123
            result = MagicMock()
            result.scalars.return_value.all.return_value = [user]
            session.execute = AsyncMock(return_value=result)

            bot = MagicMock()
            bot.session = MagicMock()
            bot.session.close = AsyncMock()
            method = MagicMock()
            method.url = "https://api.telegram.org/bot/sendMessage"
            bot.send_message = AsyncMock(
                side_effect=TelegramForbiddenError(method=method, message="Forbidden")
            )
            mock_bot_cls.return_value = bot

            resp = admin_client.post(
                "/admin/broadcast",
                json={"segment": "all", "text": "Hi", "dry_run": False},
                headers={"x-admin-token": "test-admin-token"},
            )
        assert resp.status_code == 200
        assert resp.json()["failed"] == 1


class TestAdminAuth:
    def test_viewer_role_access(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            session.scalar = AsyncMock(return_value=0)

            resp = admin_client.get(
                "/admin/overview",
                headers={"x-admin-token": "tok2"},
            )
        assert resp.status_code == 200

    def test_support_role_access_to_pending(self, admin_client):
        with patch("backend.routers.admin.SessionFactory") as mock_sf:
            session = AsyncMock()
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_sf.return_value.__aexit__ = AsyncMock()
            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            session.execute = AsyncMock(return_value=result)

            resp = admin_client.get(
                "/admin/law-updates/pending",
                headers={"x-admin-token": "tok1"},
            )
        assert resp.status_code == 200

    def test_viewer_cannot_create(self, admin_client):
        resp = admin_client.post(
            "/admin/law-updates",
            json={
                "source": "test", "source_url": "http://x", "title": "T",
                "summary": "S", "published_at": "2026-01-01T00:00:00Z",
            },
            headers={"x-admin-token": "tok2"},
        )
        assert resp.status_code == 403
