"""Ozon Seller API integration client.

Provides access to Ozon Seller API for product management,
order processing, and stock updates.
"""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class OzonSellerConfig:
    api_key: str
    client_id: str
    base_url: str = "https://api-seller.ozon.ru"
    timeout: int = 30


class OzonSellerClient:
    def __init__(self, config: OzonSellerConfig) -> None:
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

    async def get_products(self, limit: int = 100, offset: int = 0) -> dict:
        response = await self._client.post(
            "/v2/product/list",
            json={"filter": {}, "limit": limit, "offset": offset},
        )
        response.raise_for_status()
        return response.json()

    async def get_orders(self, days_back: int = 30, limit: int = 100) -> dict:
        from datetime import datetime, timedelta, timezone

        since = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
        response = await self._client.post(
            "/v3/posting/fbs/list",
            json={
                "dir": "DESC",
                "filter": {"since": since.isoformat(), "to": datetime.now(tz=timezone.utc).isoformat()},
                "limit": limit,
                "offset": 0,
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_stocks(self) -> dict:
        response = await self._client.post(
            "/v2/product/info/stocks",
            json={"filter": {}, "limit": 100},
        )
        response.raise_for_status()
        return response.json()
