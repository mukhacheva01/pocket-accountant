"""Shared fixtures for integration tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from shared.config import Settings


def _bot_mock():
    bot = MagicMock()
    bot.session = MagicMock()
    bot.session.close = AsyncMock()
    bot.set_webhook = AsyncMock()
    return bot


def make_test_settings(**overrides) -> Settings:
    base = {
        "DATABASE_URL": "sqlite+aiosqlite:///test.db",
        "REDIS_URL": "redis://localhost:6379/0",
        "TELEGRAM_BOT_TOKEN": "123456:ABC",
        "AI_ENABLED": False,
        "EXPOSE_API_DOCS": False,
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture()
def app_client():
    with patch("backend.app.build_bot_runtime") as mock_runtime:
        bot = _bot_mock()
        dp = MagicMock()
        dp.feed_update = AsyncMock()
        mock_runtime.return_value = (bot, dp)
        from backend.app import create_app
        app = create_app(settings=make_test_settings())
        with TestClient(app) as c:
            yield c
