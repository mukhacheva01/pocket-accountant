"""Repository for storing and retrieving Ozon marketplace data."""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class OzonDataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_products(self, user_id: str, products: list[dict]) -> int:
        """Save product data from Ozon sync. Returns count of saved items."""
        # TODO: implement when OzonProduct model is added
        logger.info("ozon_save_products user_id=%s count=%d", user_id, len(products))
        return len(products)

    async def save_orders(self, user_id: str, orders: list[dict]) -> int:
        """Save order data from Ozon sync. Returns count of saved items."""
        logger.info("ozon_save_orders user_id=%s count=%d", user_id, len(orders))
        return len(orders)

    async def get_revenue(self, user_id: str, since: date, until: date) -> dict:
        """Get revenue summary for date range."""
        return {"total": 0, "orders_count": 0, "returns_count": 0}

    async def get_product_count(self, user_id: str) -> int:
        """Get total number of synced products for a user."""
        return 0
