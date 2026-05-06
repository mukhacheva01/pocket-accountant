"""Integration tests for the Telegram webhook endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import make_test_settings


def _bot_mock():
    bot = MagicMock()
    bot.session = MagicMock()
    bot.session.close = AsyncMock()
    bot.set_webhook = AsyncMock()
    return bot


@pytest.fixture()
def client_no_secret():
    with patch("backend.app.build_bot_runtime") as mock_runtime:
        bot = _bot_mock()
        dp = MagicMock()
        dp.feed_update = AsyncMock()
        mock_runtime.return_value = (bot, dp)
        from backend.app import create_app
        app = create_app(settings=make_test_settings())
        with TestClient(app) as c:
            yield c


@pytest.fixture()
def client_with_secret():
    with patch("backend.app.build_bot_runtime") as mock_runtime:
        bot = _bot_mock()
        dp = MagicMock()
        dp.feed_update = AsyncMock()
        mock_runtime.return_value = (bot, dp)
        from backend.app import create_app
        app = create_app(settings=make_test_settings(TELEGRAM_WEBHOOK_SECRET="my-secret"))
        with TestClient(app) as c:
            yield c


class TestWebhookEndpoint:
    def test_webhook_no_secret_accepts(self, client_no_secret):
        payload = {"update_id": 1}
        with patch("backend.app.Update") as mock_update:
            mock_update.model_validate.return_value = MagicMock()
            resp = client_no_secret.post("/telegram/webhook", json=payload)
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}

    def test_webhook_wrong_secret_forbidden(self, client_with_secret):
        payload = {"update_id": 1}
        resp = client_with_secret.post(
            "/telegram/webhook",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        )
        assert resp.status_code == 403

    def test_webhook_correct_secret_ok(self, client_with_secret):
        payload = {"update_id": 1}
        with patch("backend.app.Update") as mock_update:
            mock_update.model_validate.return_value = MagicMock()
            resp = client_with_secret.post(
                "/telegram/webhook",
                json=payload,
                headers={"X-Telegram-Bot-Api-Secret-Token": "my-secret"},
            )
            assert resp.status_code == 200
