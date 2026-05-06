"""Tests for backend.services.rate_limit."""

from unittest.mock import AsyncMock, patch

import pytest

from shared.config import Settings


def _make_settings(**overrides) -> Settings:
    base = {"DATABASE_URL": "sqlite+aiosqlite:///test.db", "REDIS_URL": "redis://localhost:6379/0"}
    base.update(overrides)
    return Settings(**base)


class TestAllowAiRequest:
    async def test_limit_zero_allows(self):
        from backend.services.rate_limit import allow_ai_request
        s = _make_settings(AI_MAX_REQUESTS_PER_MINUTE=0)
        result = await allow_ai_request(s, "u1")
        assert result is True

    async def test_under_limit_allows(self):
        from backend.services.rate_limit import allow_ai_request
        s = _make_settings(AI_MAX_REQUESTS_PER_MINUTE=5)
        mock_client = AsyncMock()
        mock_client.incr = AsyncMock(return_value=1)
        mock_client.expire = AsyncMock()
        mock_client.aclose = AsyncMock()

        with patch("backend.services.rate_limit.redis") as mock_redis:
            mock_redis.from_url.return_value = mock_client
            result = await allow_ai_request(s, "u1")
            assert result is True

    async def test_over_limit_denies(self):
        from backend.services.rate_limit import allow_ai_request
        s = _make_settings(AI_MAX_REQUESTS_PER_MINUTE=5)
        mock_client = AsyncMock()
        mock_client.incr = AsyncMock(return_value=6)
        mock_client.aclose = AsyncMock()

        with patch("backend.services.rate_limit.redis") as mock_redis:
            mock_redis.from_url.return_value = mock_client
            result = await allow_ai_request(s, "u1")
            assert result is False
