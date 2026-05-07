"""Shared fixtures for the test suite."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from shared.config import Settings  # noqa: E402


@pytest.fixture()
def fake_settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///test.db",
        REDIS_URL="redis://localhost:6379/0",
        APP_SECRET_KEY="",
        TELEGRAM_BOT_TOKEN="123456:ABC",
        ADMIN_API_TOKEN="test-admin-token",
        ADMIN_TOKENS="admin:tok1,viewer:tok2",
        ADMIN_TELEGRAM_IDS="111,222",
        TESTER_TELEGRAM_IDS="999",
        AI_ENABLED=False,
        LLM_PROVIDER="disabled",
    )


@pytest.fixture()
def fake_async_session():
    return AsyncMock()
