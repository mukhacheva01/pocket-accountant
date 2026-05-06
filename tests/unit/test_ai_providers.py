"""Tests for OpenAIResponsesProvider and OpenRouterResponsesProvider complete()."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.ai_gateway import (
    OpenAIResponsesProvider,
    OpenRouterResponsesProvider,
)


def _fake_settings(**overrides):
    defaults = {
        "openai_api_key": "sk-test",
        "openai_model": "gpt-4o-mini",
        "openrouter_api_key": "or-test",
        "openrouter_model": "openai/gpt-4o-mini",
        "openrouter_base_url": "https://openrouter.ai/api/v1",
        "openrouter_site_url": "https://example.com",
        "openrouter_app_name": "TestApp",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _mock_response(text="Test"):
    resp = MagicMock()
    resp.output_text = text
    return resp


class TestOpenAIResponsesProviderComplete:
    async def test_complete_basic(self):
        settings = _fake_settings()
        with patch("backend.services.ai_gateway.OpenAI") as MockClient:
            mock_client = MagicMock()
            mock_client.responses.create.return_value = _mock_response("Ответ от AI")
            MockClient.return_value = mock_client

            provider = OpenAIResponsesProvider(settings)

            with patch("backend.services.ai_gateway.asyncio") as mock_asyncio:
                mock_asyncio.to_thread = AsyncMock(return_value=_mock_response("Ответ от AI"))
                resp = await provider.complete("tax_qa", {"question": "Как платить?", "profile": {}})

            assert resp.text == "Ответ от AI"
            assert resp.confidence == 0.65

    async def test_complete_with_history(self):
        settings = _fake_settings()
        with patch("backend.services.ai_gateway.OpenAI") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            provider = OpenAIResponsesProvider(settings)
            payload = {
                "question": "Test?",
                "profile": {},
                "history": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello"},
                ],
            }

            with patch("backend.services.ai_gateway.asyncio") as mock_asyncio:
                mock_asyncio.to_thread = AsyncMock(return_value=_mock_response("With history"))
                resp = await provider.complete("tax_qa", payload)

            assert resp.text == "With history"

    async def test_complete_unknown_purpose(self):
        settings = _fake_settings()
        with patch("backend.services.ai_gateway.OpenAI") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            provider = OpenAIResponsesProvider(settings)

            with patch("backend.services.ai_gateway.asyncio") as mock_asyncio:
                mock_asyncio.to_thread = AsyncMock(return_value=_mock_response("Generic"))
                resp = await provider.complete("unknown_purpose", {"question": "Q"})

            assert resp.text == "Generic"


class TestOpenRouterResponsesProviderComplete:
    async def test_complete_basic(self):
        settings = _fake_settings()
        with patch("backend.services.ai_gateway.OpenAI") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            provider = OpenRouterResponsesProvider(settings)

            with patch("backend.services.ai_gateway.asyncio") as mock_asyncio:
                mock_asyncio.to_thread = AsyncMock(return_value=_mock_response("OpenRouter ответ"))
                resp = await provider.complete("tax_qa", {"question": "Тест", "profile": {}})

            assert resp.text == "OpenRouter ответ"
            assert resp.confidence == 0.65

    async def test_complete_no_site_url(self):
        settings = _fake_settings(openrouter_site_url="", openrouter_app_name="")
        with patch("backend.services.ai_gateway.OpenAI") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            provider = OpenRouterResponsesProvider(settings)

            with patch("backend.services.ai_gateway.asyncio") as mock_asyncio:
                mock_asyncio.to_thread = AsyncMock(return_value=_mock_response("No headers"))
                resp = await provider.complete("unknown", {"question": "Q"})

            assert resp.text == "No headers"

    async def test_complete_with_long_history(self):
        settings = _fake_settings()
        with patch("backend.services.ai_gateway.OpenAI") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            provider = OpenRouterResponsesProvider(settings)
            history = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
            payload = {"question": "Q", "profile": {}, "history": history}

            with patch("backend.services.ai_gateway.asyncio") as mock_asyncio:
                mock_asyncio.to_thread = AsyncMock(return_value=_mock_response("Long history"))
                resp = await provider.complete("tax_qa", payload)

            assert resp.text == "Long history"
