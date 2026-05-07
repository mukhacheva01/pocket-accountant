"""HTTP client for bot -> backend communication via docker network."""

from __future__ import annotations

import logging
from decimal import Decimal

import httpx

from shared.config import get_settings

logger = logging.getLogger(__name__)


class BackendClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or get_settings().backend_url
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

    async def complete_onboarding(
        self, user_id: str, entity_type: str, tax_regime: str,
        has_employees: bool, region: str,
    ) -> dict:
        return await self._request("POST", f"/users/{user_id}/onboarding", json={
            "entity_type": entity_type,
            "tax_regime": tax_regime,
            "has_employees": has_employees,
            "region": region,
        })

    async def complete_onboarding_full(
        self, user_id: str, *, entity_type: str, tax_regime: str,
        has_employees: bool = False, marketplaces_enabled: bool = False,
        industry: str | None = None, region: str = "Москва",
        timezone: str = "Europe/Moscow", reminder_settings: dict | None = None,
        planning_entity: bool = False,
    ) -> dict:
        return await self._request("POST", f"/users/{user_id}/onboarding-full", json={
            "entity_type": entity_type,
            "tax_regime": tax_regime,
            "has_employees": has_employees,
            "marketplaces_enabled": marketplaces_enabled,
            "industry": industry,
            "region": region,
            "timezone": timezone,
            "reminder_settings": reminder_settings or {},
            "planning_entity": planning_entity,
        })

    async def referral_info(self, user_id: str) -> dict:
        return await self._request("GET", f"/users/{user_id}/referral-info")

    async def process_referral(self, user_id: str, referrer_telegram_id: str) -> dict:
        return await self._request("POST", f"/users/{user_id}/process-referral", json={
            "referrer_telegram_id": referrer_telegram_id,
        })

    async def save_profile(self, user_id: str, draft: dict) -> dict:
        return await self._request("POST", f"/users/{user_id}/save-profile", json=draft)

    async def record_activity(self, user_id: str, event_type: str, payload: dict | None = None) -> dict:
        return await self._request("POST", f"/users/{user_id}/activity", json={
            "event_type": event_type,
            "payload": payload or {},
        })

    # ── Events ──

    async def upcoming_events(self, user_id: str, days: int = 7) -> dict:
        return await self._request("GET", f"/events/{user_id}/upcoming", params={"days": days})

    async def overdue_events(self, user_id: str) -> dict:
        return await self._request("GET", f"/events/{user_id}/overdue")

    async def event_action(self, user_event_id: str, action: str) -> dict:
        return await self._request("POST", f"/events/{user_event_id}/action", json={"action": action})

    # ── Finance ──

    async def add_finance_record(self, user_id: str, source_text: str, record_type: str = "expense") -> dict:
        return await self._request("POST", f"/finance/{user_id}/record", json={
            "source_text": source_text,
            "record_type": record_type,
        })

    async def add_from_text(self, user_id: str, source_text: str) -> dict:
        return await self._request("POST", f"/finance/{user_id}/add-from-text", json={
            "source_text": source_text,
        })

    async def get_finance_report(self, user_id: str, days: int = 30) -> dict:
        return await self._request("GET", f"/finance/{user_id}/report", params={"days": days})

    async def get_full_report(self, user_id: str, days: int = 30) -> dict:
        return await self._request("GET", f"/finance/{user_id}/full-report", params={"days": days})

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

    async def clear_ai_history(self, user_id: str) -> dict:
        return await self._request("DELETE", f"/ai/{user_id}/history")

    async def get_ai_history(self, user_id: str, limit: int = 5) -> dict:
        return await self._request("GET", f"/ai/{user_id}/history", params={"limit": limit})

    # ── Subscription ──

    async def subscription_status(self, user_id: str) -> dict:
        return await self._request("GET", f"/subscription/{user_id}/status")

    async def activate_subscription(self, user_id: str, plan: str) -> dict:
        return await self._request("POST", f"/subscription/{user_id}/activate", params={"plan": plan})

    async def cancel_subscription(self, user_id: str) -> dict:
        return await self._request("POST", f"/subscription/{user_id}/cancel")

    async def record_payment(self, user_id: str, amount: str, currency: str = "RUB", provider: str = "manual") -> dict:
        return await self._request("POST", f"/subscription/{user_id}/payment", json={
            "amount": amount,
            "currency": currency,
            "provider": provider,
        })

    async def process_payment(
        self, user_id: str, plan: str, amount: int, charge_id: str,
    ) -> dict:
        return await self._request("POST", f"/subscription/{user_id}/process-payment", json={
            "plan": plan,
            "amount": amount,
            "charge_id": charge_id,
        })

    # ── Tax ──

    async def calculate_tax(
        self, regime: str, income: Decimal, expenses: Decimal = Decimal("0"),
        entity_type: str | None = None, has_employees: bool = False,
    ) -> dict:
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

    async def compare_regimes(
        self, activity: str, monthly_income: Decimal,
        has_employees: bool = False, counterparties: str = "mixed",
        region: str = "Москва",
    ) -> dict:
        return await self._request("POST", "/tax/compare-regimes", json={
            "activity": activity,
            "monthly_income": str(monthly_income),
            "has_employees": has_employees,
            "counterparties": counterparties,
            "region": region,
        })

    # ── Documents ──

    async def upcoming_documents(self, user_id: str) -> dict:
        return await self._request("GET", f"/documents/{user_id}/upcoming")

    async def match_template(self, text: str) -> dict:
        return await self._request("POST", "/documents/match-template", json={"text": text})

    # ── Laws ──

    async def relevant_laws(self, user_id: str) -> dict:
        return await self._request("GET", f"/laws/{user_id}/relevant")
