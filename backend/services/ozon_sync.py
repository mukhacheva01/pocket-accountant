"""Ozon data synchronization service.

Pulls product, order, and stock data from Ozon Seller API
and stores it in the local database.
"""

import logging

logger = logging.getLogger(__name__)


class OzonSyncService:
    def __init__(self, ozon_data_repo, ozon_seller_client=None) -> None:
        self._repo = ozon_data_repo
        self._client = ozon_seller_client

    async def sync_products(self, user_id: str) -> int:
        """Sync products from Ozon API. Returns count of synced items."""
        if self._client is None:
            logger.warning("ozon_seller_client not configured, skipping sync")
            return 0
        data = await self._client.get_products()
        items = data.get("result", {}).get("items", [])
        return await self._repo.save_products(user_id, items)

    async def sync_orders(self, user_id: str, days_back: int = 30) -> int:
        """Sync orders from Ozon API. Returns count of synced items."""
        if self._client is None:
            logger.warning("ozon_seller_client not configured, skipping sync")
            return 0
        data = await self._client.get_orders(days_back=days_back)
        postings = data.get("result", {}).get("postings", [])
        return await self._repo.save_orders(user_id, postings)

    async def full_sync(self, user_id: str) -> dict:
        """Run full data sync. Returns summary of synced items."""
        products = await self.sync_products(user_id)
        orders = await self.sync_orders(user_id)
        logger.info("ozon_full_sync user_id=%s products=%d orders=%d", user_id, products, orders)
        return {"products": products, "orders": orders}
