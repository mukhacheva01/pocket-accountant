"""Tests for backend.services.ai_gateway."""


from backend.services.ai_gateway import (
    AIGateway,
    AIResponse,
    NoopAIProvider,
    build_ai_provider,
)
from shared.config import Settings


def _make_settings(**overrides) -> Settings:
    base = {"DATABASE_URL": "sqlite+aiosqlite:///test.db", "REDIS_URL": "redis://localhost:6379/0"}
    base.update(overrides)
    return Settings(**base)


class TestNoopAIProvider:
    async def test_returns_unavailable_message(self):
        provider = NoopAIProvider()
        response = await provider.complete("tax_qa", {})
        assert isinstance(response, AIResponse)
        assert "недоступен" in response.text
        assert response.confidence == 0.0
        assert response.sources == []


class TestAIGateway:
    async def test_answer_tax_question_success(self):
        class FakeProvider:
            async def complete(self, purpose, payload):
                return AIResponse(text="Ответ", sources=[], confidence=0.8)

        gw = AIGateway(FakeProvider())
        resp = await gw.answer_tax_question("вопрос", {"entity_type": "ip"})
        assert "Ответ" in resp.text
        assert "Справочная" in resp.text

    async def test_answer_tax_question_with_history(self):
        class FakeProvider:
            async def complete(self, purpose, payload):
                assert "history" in payload
                return AIResponse(text="OK", sources=[], confidence=0.5)

        gw = AIGateway(FakeProvider())
        resp = await gw.answer_tax_question("вопрос", {}, history=[{"role": "user", "content": "prev"}])
        assert "OK" in resp.text

    async def test_answer_tax_question_error(self):
        class FailingProvider:
            async def complete(self, purpose, payload):
                raise RuntimeError("boom")

        gw = AIGateway(FailingProvider())
        resp = await gw.answer_tax_question("вопрос", {})
        assert "недоступен" in resp.text
        assert resp.confidence == 0.0


class TestBuildAiProvider:
    def test_disabled(self):
        s = _make_settings(AI_ENABLED=False)
        provider = build_ai_provider(s)
        assert isinstance(provider, NoopAIProvider)

    def test_openrouter_without_key(self):
        s = _make_settings(AI_ENABLED=True, LLM_PROVIDER="openrouter", OPENROUTER_API_KEY="")
        provider = build_ai_provider(s)
        assert isinstance(provider, NoopAIProvider)

    def test_openai_without_key(self):
        s = _make_settings(AI_ENABLED=True, LLM_PROVIDER="openai", OPENAI_API_KEY="")
        provider = build_ai_provider(s)
        assert isinstance(provider, NoopAIProvider)
