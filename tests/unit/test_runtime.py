"""Tests for bot.runtime."""

from bot.runtime import build_bot_runtime
from shared.config import Settings


def _make_settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///test.db",
        REDIS_URL="redis://localhost:6379/0",
        TELEGRAM_BOT_TOKEN="123456:ABC",
    )


def test_build_bot_runtime():
    bot, dispatcher = build_bot_runtime(_make_settings())
    assert bot is not None
    assert dispatcher is not None
