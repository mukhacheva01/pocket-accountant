"""Tests for backend.services.marketplace_connections."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.services.marketplace_connections import MarketplaceConnectionService, OzonConnectionDraft
from shared.secrets import SecretBox


@pytest.fixture()
def svc():
    repo = AsyncMock()
    box = SecretBox("", allow_insecure_fallback=True)
    return MarketplaceConnectionService(repo, box)


class TestMaskApiKey:
    def test_short_key(self):
        assert MarketplaceConnectionService.mask_api_key("abc") == "***"

    def test_long_key(self):
        masked = MarketplaceConnectionService.mask_api_key("abcdefghijkl")
        assert masked == "abcd***ijkl"

    def test_exactly_8(self):
        assert MarketplaceConnectionService.mask_api_key("12345678") == "********"


class TestLoadOzonConnection:
    async def test_no_connection(self, svc):
        svc.connections.get_by_user_id.return_value = None
        result = await svc.load_ozon_connection("u1")
        assert result is None

    async def test_with_connection(self, svc):
        conn = SimpleNamespace(api_key_secret="plainkey")
        svc.connections.get_by_user_id.return_value = conn
        result = await svc.load_ozon_connection("u1")
        assert result.api_key_secret == "plainkey"


class TestSaveOzonConnection:
    async def test_save(self, svc):
        draft = OzonConnectionDraft(seller_id="S123", api_key_secret="secret_key_value")
        await svc.save_ozon_connection("u1", draft)
        svc.connections.upsert.assert_awaited_once()
        call_data = svc.connections.upsert.call_args[0][1]
        assert call_data["seller_id"] == "S123"
        assert call_data["api_key_masked"] == "secr***alue"
        assert call_data["status"] == "pending"
