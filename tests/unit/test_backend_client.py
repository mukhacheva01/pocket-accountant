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

    async def test_ensure_user(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"id": "u1"}
            result = await client.ensure_user(123, "nick", "Name")
            mock_req.assert_awaited_once_with("POST", "/users/ensure", json={
                "telegram_id": 123, "username": "nick", "first_name": "Name", "timezone": "Europe/Moscow",
            })
            assert result["id"] == "u1"

    async def test_get_profile(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"entity_type": "ip"}
            result = await client.get_profile("u1")
            mock_req.assert_awaited_once_with("GET", "/users/u1/profile")
            assert result["entity_type"] == "ip"

    async def test_complete_onboarding(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"ok": True}
            result = await client.complete_onboarding("u1", "ip", "usn_income", False, "Moscow")
            assert result["ok"]

    async def test_upcoming_events(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"events": []}
            result = await client.upcoming_events("u1", days=14)
            mock_req.assert_awaited_once_with("GET", "/events/u1/upcoming", params={"days": 14})

    async def test_event_action(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"ok": True}
            result = await client.event_action("ev1", "done")
            mock_req.assert_awaited_once()

    async def test_add_finance_record(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"id": "rec1"}
            result = await client.add_finance_record("u1", "получил 5000", "income")
            assert result["id"] == "rec1"

    async def test_get_finance_report(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"totals": {}}
            await client.get_finance_report("u1", days=7)
            mock_req.assert_awaited_once()

    async def test_get_finance_records(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"records": []}
            await client.get_finance_records("u1", record_type="income", limit=10)
            mock_req.assert_awaited_once()

    async def test_ask_ai(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"text": "answer"}
            result = await client.ask_ai("u1", "вопрос", history=[])
            assert result["text"] == "answer"

    async def test_subscription_status(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"plan": "free"}
            result = await client.subscription_status("u1")
            assert result["plan"] == "free"

    async def test_activate_subscription(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"ok": True}
            await client.activate_subscription("u1", "basic")
            mock_req.assert_awaited_once()

    async def test_calculate_tax(self, client):
        from decimal import Decimal
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"tax": "30000"}
            await client.calculate_tax("usn6", Decimal("500000"))
            mock_req.assert_awaited_once()

    async def test_parse_tax_query(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"result": {}}
            await client.parse_tax_query("усн 6 доход 500к", profile={})
            mock_req.assert_awaited_once()

    async def test_track_activity(self, client):
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {
                "user": {"id": "u1"}, "profile": None, "subscription": None,
            }
            result = await client.track_activity(
                telegram_id=123,
                username="alice",
                first_name="Alice",
                event_type="command",
                payload={"command": "start"},
            )
            mock_req.assert_awaited_once_with("POST", "/users/activity", json={
                "telegram_id": 123,
                "username": "alice",
                "first_name": "Alice",
                "event_type": "command",
                "payload": {"command": "start"},
            })
            assert result["user"]["id"] == "u1"
