import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Deque, Dict, List, Optional, Protocol

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    text: str
    sources: List[Dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0


class AIProvider(Protocol):
    async def complete(self, purpose: str, payload: Dict[str, object]) -> AIResponse:
        ...


class AIRateLimitError(RuntimeError):
    pass


class NoopAIProvider:
    def __init__(self, message: Optional[str] = None) -> None:
        self.message = message or (
            "AI-режим MP-Pilot сейчас отключён. "
            "Когда будет нужен AI, подключим OpenRouter и включим AI_ENABLED=true."
        )

    async def complete(self, purpose: str, payload: Dict[str, object]) -> AIResponse:
        return AIResponse(text=self.message, sources=[], confidence=0.0)


class RateLimitedProvider:
    def __init__(self, provider: AIProvider, max_requests_per_minute: int) -> None:
        self.provider = provider
        self.max_requests_per_minute = max(1, max_requests_per_minute)
        self._timestamps: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def complete(self, purpose: str, payload: Dict[str, object]) -> AIResponse:
        await self._check_rate_limit()
        return await self.provider.complete(purpose, payload)

    async def _check_rate_limit(self) -> None:
        now = time.monotonic()
        async with self._lock:
            while self._timestamps and now - self._timestamps[0] >= 60:
                self._timestamps.popleft()
            if len(self._timestamps) >= self.max_requests_per_minute:
                raise AIRateLimitError("AI limit reached")
            self._timestamps.append(now)


class OpenAICompatibleResponsesProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float = 30.0,
        base_url: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.model = model
        client_kwargs = {
            "api_key": api_key,
            "timeout": timeout,
        }
        if base_url:
            client_kwargs["base_url"] = base_url
        if default_headers:
            client_kwargs["default_headers"] = default_headers
        self.client = OpenAI(**client_kwargs)

    async def complete(self, purpose: str, payload: Dict[str, object]) -> AIResponse:
        instructions = self._instructions_for(purpose)

        def _request():
            return self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=json.dumps(payload, ensure_ascii=False, default=str),
                store=False,
            )

        response = await asyncio.to_thread(_request)
        return AIResponse(text=response.output_text.strip(), sources=[], confidence=0.65)

    @staticmethod
    def _instructions_for(purpose: str) -> str:
        if purpose == "seller_qa":
            return (
                "Ты MP-Pilot, AI-ассистент для селлеров Ozon. "
                "Отвечай коротко, структурированно и по делу. "
                "Сначала опирайся на данные магазина из payload. "
                "Если данных не хватает, прямо скажи, чего именно не хватает. "
                "Не обещай гарантированный рост. "
                "Для расчётов используй структуру: вводные -> расчет -> вывод -> следующий шаг. "
                "Для карточек и контента используй структуру: проблема -> что исправить -> ожидаемый эффект."
            )
        return "Return a concise and actionable answer."


class OpenAIResponsesProvider(OpenAICompatibleResponsesProvider):
    def __init__(self, *, api_key: str, model: str, timeout: float) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            timeout=timeout,
        )


class OpenRouterResponsesProvider(OpenAICompatibleResponsesProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float,
        base_url: str,
        site_url: str,
        app_name: str,
    ) -> None:
        headers: Dict[str, str] = {}
        if site_url:
            headers["HTTP-Referer"] = site_url
        if app_name:
            headers["X-Title"] = app_name
        super().__init__(
            api_key=api_key,
            model=model,
            timeout=timeout,
            base_url=base_url,
            default_headers=headers or None,
        )


class AIGateway:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    async def answer_seller_question(self, question: str, profile: Dict[str, object]) -> AIResponse:
        try:
            response = await self.provider.complete(
                "seller_qa",
                {"question": question, "profile": profile},
            )
        except AIRateLimitError:
            response = AIResponse(
                text="Лимит AI-запросов за минуту достигнут. Повтори запрос чуть позже.",
                sources=[],
                confidence=0.0,
            )
        except Exception:
            logger.exception("ai_completion_failed")
            response = AIResponse(
                text=(
                    "AI-ответ сейчас недоступен. "
                    "Проверь подключение провайдера или повтори запрос позже."
                ),
                sources=[],
                confidence=0.0,
            )

        disclaimer = (
            "\n\nЭто справочный ответ. Для решений по тарифам, комиссиям, логистике и правилам Ozon "
            "сверяйся с актуальной документацией кабинета и фактическими данными магазина."
        )
        return AIResponse(
            text=(response.text or "").strip() + disclaimer,
            sources=response.sources,
            confidence=response.confidence,
        )


@lru_cache(maxsize=8)
def _build_cached_provider(
    *,
    ai_enabled: bool,
    provider_name: str,
    openai_api_key: str,
    openai_model: str,
    openrouter_api_key: str,
    openrouter_model: str,
    openrouter_base_url: str,
    openrouter_site_url: str,
    openrouter_app_name: str,
    llm_timeout_seconds: float,
    ai_max_requests_per_minute: int,
) -> AIProvider:
    if not ai_enabled:
        return NoopAIProvider()

    provider_name = provider_name.strip().lower()
    if provider_name == "openrouter":
        if not openrouter_api_key:
            return NoopAIProvider("AI включён, но OPENROUTER_API_KEY ещё не задан.")
        return RateLimitedProvider(
            OpenRouterResponsesProvider(
                api_key=openrouter_api_key,
                model=openrouter_model,
                timeout=llm_timeout_seconds,
                base_url=openrouter_base_url,
                site_url=openrouter_site_url,
                app_name=openrouter_app_name,
            ),
            ai_max_requests_per_minute,
        )
    if provider_name == "openai":
        if not openai_api_key:
            return NoopAIProvider("AI включён, но OPENAI_API_KEY ещё не задан.")
        return RateLimitedProvider(
            OpenAIResponsesProvider(
                api_key=openai_api_key,
                model=openai_model,
                timeout=llm_timeout_seconds,
            ),
            ai_max_requests_per_minute,
        )
    return NoopAIProvider("AI-провайдер не настроен. Поддерживаются openrouter и openai.")


def build_ai_provider(settings) -> AIProvider:
    return _build_cached_provider(
        ai_enabled=settings.ai_enabled,
        provider_name=settings.resolved_llm_provider,
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_model=settings.openrouter_model,
        openrouter_base_url=settings.openrouter_base_url,
        openrouter_site_url=settings.openrouter_site_url,
        openrouter_app_name=settings.openrouter_app_name,
        llm_timeout_seconds=settings.llm_timeout_seconds,
        ai_max_requests_per_minute=settings.ai_max_requests_per_minute,
    )
