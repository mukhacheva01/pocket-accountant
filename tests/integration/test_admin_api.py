"""Integration tests for admin endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from shared.config import Settings, get_settings


def _bot_mock():
    bot = MagicMock()
    bot.session = MagicMock()
    bot.session.close = AsyncMock()
    bot.set_webhook = AsyncMock()
    return bot


def _settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///test.db",
        REDIS_URL="redis://localhost:6379/0",
        TELEGRAM_BOT_TOKEN="123456:ABC",
        ADMIN_API_TOKEN="test-admin-token",
        ADMIN_TOKENS="admin:tok1",
        ADMIN_TELEGRAM_IDS="111",
        AI_ENABLED=False,
        EXPOSE_API_DOCS=False,
    )


@pytest.fixture()
def admin_client():
    settings = _settings()
    with patch("backend.app.build_bot_runtime") as mock_runtime:
        bot = _bot_mock()
        dp = MagicMock()
        dp.feed_update = AsyncMock()
        mock_runtime.return_value = (bot, dp)
        from backend.app import create_app
        app = create_app(settings=settings)
        app.dependency_overrides[get_settings] = lambda: settings
        with TestClient(app) as c:
            yield c


class TestAdminHealth:
    def test_forbidden_without_token(self, admin_client):
        resp = admin_client.get("/admin/health")
        assert resp.status_code == 403

    def test_ok_with_admin_token(self, admin_client):
        resp = admin_client.get("/admin/health", headers={"X-Admin-Token": "test-admin-token"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_ok_with_role_token(self, admin_client):
        resp = admin_client.get("/admin/health", headers={"X-Admin-Token": "tok1"})
        assert resp.status_code == 200
