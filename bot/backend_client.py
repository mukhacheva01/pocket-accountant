"""HTTP client for bot -> backend communication via docker network."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BackendClient:
    def __init__(self, base_url: str = "http://backend:8080") -> None:
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        client = await self._get_client()
        response = await client.request(method, f"/api{path}", **kwargs)
        response.raise_for_status()
        return response.json()

    # ── Users ──

    async def ensure_user(
        self, telegram_id: int, username: str | None, first_name: str | None, timezone: str = "Europe/Moscow",
    ) -> dict:
        return await self._request("POST", "/users/ensure", json={
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "timezone": timezone,
        })

    async def get_profile(self, user_id: str) -> dict:
        return await self._request("GET", f"/users/{user_id}/profile")

    async def complete_onboarding(self, user_id: str, entity_type: str, tax_regime: str, has_employees: bool, region: str) -> dict:
        return await self._request("POST", f"/users/{user_id}/onboarding", json={
            "entity_type": entity_type,
            "tax_regime": tax_regime,
            "has_employees": has_employees,
            "region": region,
        })

    # ── Events ──

    async def upcoming_events(self, user_id: str, days: int = 7) -> dict:
        return await self._request("GET", f"/events/{user_id}/upcoming", params={"days": days})

    async def event_action(self, user_event_id: str, action: str) -> dict:
        return await self._request("POST", f"/events/{user_event_id}/action", json={"action": action})

    # ── Finance ──

    async def add_finance_record(self, user_id: str, source_text: str, record_type: str) -> dict:
        return await self._request("POST", f"/finance/{user_id}/record", json={
            "source_text": source_text,
            "record_type": record_type,
        })

    async def get_finance_report(self, user_id: str, days: int = 30) -> dict:
        return await self._request("GET", f"/finance/{user_id}/report", params={"days": days})

    async def get_finance_records(self, user_id: str, record_type: str = "all", limit: int = 20) -> dict:
        return await self._request("GET", f"/finance/{user_id}/records", params={
            "record_type": record_type,
            "limit": limit,
        })

    # ── AI ──

    async def ask_ai(self, user_id: str, question: str, history: list | None = None) -> dict:
        return await self._request("POST", f"/ai/{user_id}/question", json={
            "question": question,
            "history": history or [],
        })

    # ── Subscription ──

    async def subscription_status(self, user_id: str) -> dict:
        return await self._request("GET", f"/subscription/{user_id}/status")

    async def activate_subscription(self, user_id: str, plan: str) -> dict:
        return await self._request("POST", f"/subscription/{user_id}/activate", params={"plan": plan})

    # ── Tax ──

    async def calculate_tax(self, regime: str, income: Decimal, expenses: Decimal = Decimal("0"),
                            entity_type: str | None = None, has_employees: bool = False) -> dict:
        return await self._request("POST", "/tax/calculate", json={
            "regime": regime,
            "income": str(income),
            "expenses": str(expenses),
            "entity_type": entity_type,
            "has_employees": has_employees,
        })

    async def parse_tax_query(self, query: str, profile: dict | None = None) -> dict:
        return await self._request("POST", "/tax/parse-query", json={
            "query": query,
            "profile": profile or {},
        })
