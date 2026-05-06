"""Extended tests for backend.services.ai_gateway."""

from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.ai_gateway import AIGateway, AIResponse, NoopAIProvider, OpenAIResponsesProvider


class TestNoopAIProvider:
    async def test_returns_unavailable(self):
        provider = NoopAIProvider()
        response = await provider.complete("tax_qa", {"question": "test"})
        assert "недоступен" in response.text
        assert response.confidence == 0.0
        assert response.sources == []


class TestAIGateway:
    async def test_answer_adds_disclaimer(self):
        provider = AsyncMock()
        provider.complete = AsyncMock(return_value=AIResponse(text="Ответ", sources=[], confidence=0.7))
        gw = AIGateway(provider)
        response = await gw.answer_tax_question("Вопрос", {"entity_type": "ip"})
        assert "Справочная информация" in response.text
        assert response.confidence == 0.7

    async def test_answer_with_history(self):
        provider = AsyncMock()
        provider.complete = AsyncMock(return_value=AIResponse(text="OK", sources=[], confidence=0.5))
        gw = AIGateway(provider)
        history = [{"role": "user", "content": "Привет"}, {"role": "assistant", "content": "Здравствуй"}]
        response = await gw.answer_tax_question("Как платить?", {}, history)
        assert "OK" in response.text

    async def test_answer_handles_error(self):
        provider = AsyncMock()
        provider.complete = AsyncMock(side_effect=RuntimeError("API down"))
        gw = AIGateway(provider)
        response = await gw.answer_tax_question("Вопрос", {})
        assert "недоступен" in response.text
        assert response.confidence == 0.0


class TestOpenAIResponsesProvider:
    def test_instructions_for_tax_qa(self):
        instructions = OpenAIResponsesProvider._instructions_for("tax_qa")
        assert "Карманный Бухгалтер" in instructions
        assert "2026" in instructions

    def test_instructions_for_unknown(self):
        instructions = OpenAIResponsesProvider._instructions_for("unknown")
        assert instructions == "Return a concise answer."


class TestBuildAIProvider:
    def test_disabled_returns_noop(self):
        from backend.services.ai_gateway import build_ai_provider
        settings = MagicMock()
        settings.ai_enabled = False
        provider = build_ai_provider(settings)
        assert isinstance(provider, NoopAIProvider)

    def test_openai_no_key_returns_noop(self):
        from backend.services.ai_gateway import build_ai_provider
        settings = MagicMock()
        settings.ai_enabled = True
        settings.llm_provider = "openai"
        settings.openai_api_key = ""
        provider = build_ai_provider(settings)
        assert isinstance(provider, NoopAIProvider)

    def test_openai_with_key_returns_provider(self):
        from backend.services.ai_gateway import build_ai_provider
        settings = MagicMock()
        settings.ai_enabled = True
        settings.llm_provider = "openai"
        settings.openai_api_key = "sk-test"
        settings.openai_model = "gpt-4o-mini"
        provider = build_ai_provider(settings)
        assert isinstance(provider, OpenAIResponsesProvider)

    def test_openrouter_with_key_returns_provider(self):
        from backend.services.ai_gateway import build_ai_provider, OpenRouterResponsesProvider
        settings = MagicMock()
        settings.ai_enabled = True
        settings.llm_provider = "openrouter"
        settings.openrouter_api_key = "or-test"
        settings.openrouter_model = "model"
        settings.openrouter_base_url = "https://api.openrouter.ai/v1"
        settings.openrouter_site_url = ""
        settings.openrouter_app_name = ""
        provider = build_ai_provider(settings)
        assert isinstance(provider, OpenRouterResponsesProvider)

    def test_openrouter_no_key_returns_noop(self):
        from backend.services.ai_gateway import build_ai_provider
        settings = MagicMock()
        settings.ai_enabled = True
        settings.llm_provider = "openrouter"
        settings.openrouter_api_key = ""
        provider = build_ai_provider(settings)
        assert isinstance(provider, NoopAIProvider)
