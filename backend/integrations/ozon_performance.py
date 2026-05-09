"""Ozon Performance (Ads) API integration client.

Provides access to Ozon advertising/performance API for
campaign management and analytics.
"""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class OzonPerformanceConfig:
    api_key: str
    client_id: str
    base_url: str = "https://api-performance.ozon.ru"
    timeout: int = 30


class OzonPerformanceClient:
    def __init__(self, config: OzonPerformanceConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            headers={
                "Api-Key": config.api_key,
                "Client-Id": config.client_id,
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_campaigns(self) -> dict:
        response = await self._client.get("/api/client/campaign")
        response.raise_for_status()
        return response.json()

    async def get_campaign_stats(self, campaign_ids: list[str], date_from: str, date_to: str) -> dict:
        response = await self._client.post(
            "/api/client/statistics",
            json={
                "campaigns": campaign_ids,
                "dateFrom": date_from,
                "dateTo": date_to,
            },
        )
        response.raise_for_status()
        return response.json()
