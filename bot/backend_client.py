"""HTTP client for bot → backend communication.

Stub for Phase 1. Full implementation in Phase 2.
"""

from __future__ import annotations

import httpx


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
