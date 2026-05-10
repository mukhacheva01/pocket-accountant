"""HTTP client for bot -> backend communication via docker network.

All bot data access goes through this client — the bot never imports
shared.db or backend.services directly.
"""

from __future__ import annotations

import logging
from decimal import Decimal

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

    # ── User activity (middleware) ──

    async def track_activity(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        event_type: str = "message",
        payload: dict | None = None,
        command: str | None = None,
    ) -> dict:
        return await self._request("POST", "/bot/users/track-activity", json={
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "event_type": event_type,
            "payload": payload or {},
            "command": command,
        })

    # ── Aggregated views ──

    async def get_home(self, telegram_id: int) -> dict:
        return await self._request("GET", f"/bot/users/{telegram_id}/home")

    async def get_profile(self, telegram_id: int) -> dict:
        return await self._request("GET", f"/bot/users/{telegram_id}/profile")

    # ── Events ──

    async def get_events(self, telegram_id: int, days: int = 14) -> dict:
        return await self._request("GET", f"/bot/events/{telegram_id}/list", params={"days": days})

    async def get_calendar(self, telegram_id: int, days: int = 30) -> dict:
        return await self._request("GET", f"/bot/events/{telegram_id}/calendar", params={"days": days})

    async def get_overdue(self, telegram_id: int) -> dict:
        return await self._request("GET", f"/bot/events/{telegram_id}/overdue")

    async def event_snooze(self, user_event_id: str) -> dict:
        return await self._request("POST", f"/bot/events/{user_event_id}/snooze")

    async def event_complete(self, user_event_id: str) -> dict:
        return await self._request("POST", f"/bot/events/{user_event_id}/complete")

    # ── Finance ──

    async def get_finance_report(self, telegram_id: int, days: int = 30) -> dict:
        return await self._request("GET", f"/bot/finance/{telegram_id}/report", params={"days": days})

    async def get_balance(self, telegram_id: int) -> dict:
        return await self._request("GET", f"/bot/finance/{telegram_id}/balance")

    async def get_finance_records(self, telegram_id: int, record_type: str = "all", limit: int = 20) -> dict:
        return await self._request("GET", f"/bot/finance/{telegram_id}/records", params={
            "record_type": record_type,
            "limit": limit,
        })

    async def add_from_text(self, telegram_id: int, source_text: str) -> dict:
        return await self._request("POST", f"/bot/finance/{telegram_id}/add-from-text", json={
            "source_text": source_text,
            "record_kind": "auto",
        })

    # ── Documents / Laws / Reminders ──

    async def get_documents(self, telegram_id: int) -> dict:
        return await self._request("GET", f"/bot/users/{telegram_id}/documents")

    async def get_laws(self, telegram_id: int) -> dict:
        return await self._request("GET", f"/bot/users/{telegram_id}/laws")

    async def get_reminders(self, telegram_id: int) -> dict:
        return await self._request("GET", f"/bot/users/{telegram_id}/reminders")

    # ── AI ──

    async def ai_full_question(self, telegram_id: int, question: str) -> dict:
        return await self._request("POST", f"/bot/ai/{telegram_id}/full-question", json={
            "question": question,
            "answer": "",
            "sources": [],
        })

    async def ai_clear_history(self, telegram_id: int) -> dict:
        return await self._request("DELETE", f"/bot/ai/{telegram_id}/history")

    # ── Subscription ──

    async def get_subscription_status(self, telegram_id: int) -> dict:
        return await self._request("GET", f"/bot/subscription/{telegram_id}/full-status")

    async def cancel_subscription(self, telegram_id: int) -> dict:
        return await self._request("POST", f"/bot/subscription/{telegram_id}/cancel")

    async def activate_subscription(self, telegram_id: int, plan: str) -> dict:
        return await self._request("POST", f"/bot/subscription/{telegram_id}/activate", params={"plan": plan})

    async def record_payment(
        self, telegram_id: int, plan: str, amount: int, charge_id: str,
    ) -> dict:
        return await self._request("POST", f"/bot/subscription/{telegram_id}/record-payment", json={
            "plan": plan,
            "amount": amount,
            "charge_id": charge_id,
        })

    # ── Referral ──

    async def get_referral(self, telegram_id: int) -> dict:
        return await self._request("GET", f"/bot/users/{telegram_id}/referral")

    async def save_referral(self, telegram_id: int, referrer_telegram_id: str) -> dict:
        return await self._request("POST", f"/bot/users/{telegram_id}/referral", json={
            "referrer_telegram_id": referrer_telegram_id,
        })

    # ── Onboarding ──

    async def onboarding_with_sync(
        self,
        telegram_id: int,
        entity_type: str,
        tax_regime: str,
        has_employees: bool = False,
        region: str = "Москва",
        timezone: str = "Europe/Moscow",
        reminder_settings: dict | None = None,
        marketplaces_enabled: bool = False,
        industry: str | None = None,
    ) -> dict:
        return await self._request("POST", f"/bot/users/{telegram_id}/onboarding-with-sync", json={
            "entity_type": entity_type,
            "tax_regime": tax_regime,
            "has_employees": has_employees,
            "region": region,
            "timezone": timezone,
            "reminder_settings": reminder_settings or {},
            "marketplaces_enabled": marketplaces_enabled,
            "industry": industry,
        })

    # ── Tax ──

    async def compare_regimes(
        self,
        activity: str,
        monthly_income: str,
        has_employees: bool = False,
        counterparties: str = "mixed",
        region: str = "Москва",
    ) -> dict:
        return await self._request("POST", "/bot/tax/compare-regimes", json={
            "activity": activity,
            "monthly_income": monthly_income,
            "has_employees": has_employees,
            "counterparties": counterparties,
            "region": region,
        })

    async def parse_and_calculate_tax(self, telegram_id: int, query: str) -> dict:
        return await self._request(
            "POST", "/bot/tax/parse-and-calculate",
            params={"telegram_id": telegram_id, "query": query},
        )

    # ── Templates ──

    async def match_template(self, text: str) -> dict:
        return await self._request("POST", "/bot/templates/match", json={"text": text})
