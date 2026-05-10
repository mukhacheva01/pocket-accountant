"""Tests for bot.backend_client.BackendClient."""

from unittest.mock import AsyncMock, patch

import pytest

from bot.backend_client import BackendClient


@pytest.fixture()
def client():
    return BackendClient(base_url="http://test:8080")


class TestBackendClient:
    async def test_get_client_creates_once(self, client):
        c1 = await client._get_client()
        c2 = await client._get_client()
        assert c1 is c2
        await client.close()

    async def test_close_idempotent(self, client):
        await client.close()
        await client.close()

    async def test_track_activity(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"ok": True, "user_id": "u1"}
            result = await client.track_activity(123, username="nick", first_name="Name")
            mock_req.assert_awaited_once_with("POST", "/bot/users/track-activity", json={
                "telegram_id": 123, "username": "nick", "first_name": "Name",
                "event_type": "message", "payload": {}, "command": None,
            })
            assert result["ok"]

    async def test_get_home(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"has_profile": True}
            result = await client.get_home(123)
            mock_req.assert_awaited_once_with("GET", "/bot/users/123/home")
            assert result["has_profile"]

    async def test_get_profile(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"has_profile": True, "profile": {"entity_type": "ip"}}
            result = await client.get_profile(123)
            mock_req.assert_awaited_once_with("GET", "/bot/users/123/profile")
            assert result["profile"]["entity_type"] == "ip"

    async def test_get_events(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"events": []}
            result = await client.get_events(123, days=14)
            mock_req.assert_awaited_once_with("GET", "/bot/events/123/list", params={"days": 14})

    async def test_event_snooze(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"ok": True}
            await client.event_snooze("ev1")
            mock_req.assert_awaited_once_with("POST", "/bot/events/ev1/snooze")

    async def test_get_finance_report(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"income": "0", "expense": "0"}
            await client.get_finance_report(123, days=7)
            mock_req.assert_awaited_once()

    async def test_get_finance_records(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"records": []}
            await client.get_finance_records(123, record_type="income", limit=10)
            mock_req.assert_awaited_once()

    async def test_add_from_text(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"ok": True, "record_type": "income"}
            result = await client.add_from_text(123, "получил 5000")
            assert result["ok"]

    async def test_ai_full_question(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"ok": True, "answer": "ответ"}
            result = await client.ai_full_question(123, "вопрос")
            assert result["answer"] == "ответ"

    async def test_ai_clear_history(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"ok": True}
            await client.ai_clear_history(123)
            mock_req.assert_awaited_once_with("DELETE", "/bot/ai/123/history")

    async def test_get_subscription_status(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"is_active": False}
            result = await client.get_subscription_status(123)
            assert not result["is_active"]

    async def test_activate_subscription(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"ok": True}
            await client.activate_subscription(123, "basic")
            mock_req.assert_awaited_once()

    async def test_record_payment(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"ok": True, "expires_at": "2025-02-01"}
            result = await client.record_payment(123, "basic", 150, "charge_123")
            assert result["ok"]

    async def test_get_referral(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"referral_count": 2}
            result = await client.get_referral(123)
            assert result["referral_count"] == 2

    async def test_onboarding_with_sync(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"ok": True}
            result = await client.onboarding_with_sync(123, "ip", "usn_income")
            assert result["ok"]

    async def test_compare_regimes(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"rendered": "result"}
            result = await client.compare_regimes("services", "300000")
            assert result["rendered"] == "result"

    async def test_match_template(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"matched": False}
            result = await client.match_template("hello")
            assert not result["matched"]
