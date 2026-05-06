from dataclasses import dataclass
from datetime import datetime, timezone

from accountant_bot.core.secrets import SecretBox
from accountant_bot.repositories.marketplace_connections import MarketplaceConnectionRepository


@dataclass
class OzonConnectionDraft:
    seller_id: str
    api_key_secret: str


class MarketplaceConnectionService:
    def __init__(self, connections: MarketplaceConnectionRepository, secret_box: SecretBox) -> None:
        self.connections = connections
        self.secret_box = secret_box

    async def load_ozon_connection(self, user_id: str):
        connection = await self.connections.get_by_user_id(user_id)
        if connection and connection.api_key_secret:
            connection.api_key_secret = self.secret_box.decrypt(connection.api_key_secret)
        return connection

    async def save_ozon_connection(self, user_id: str, draft: OzonConnectionDraft):
        encrypted = self.secret_box.encrypt(draft.api_key_secret)
        return await self.connections.upsert(
            user_id,
            {
                "provider": "ozon",
                "seller_id": draft.seller_id,
                "api_key_secret": encrypted,
                "api_key_masked": self.mask_api_key(draft.api_key_secret),
                "status": "pending",
                "status_message": "Ключ сохранен. Автоматическая первичная синхронизация еще не реализована в backend.",
                "sync_requested_at": datetime.now(timezone.utc),
                "last_synced_at": None,
                "last_error": None,
                "synced_cards": 0,
                "synced_orders": 0,
                "synced_stocks": 0,
                "sync_meta": {
                    "sync_mode": "manual_placeholder",
                },
            },
        )

    @staticmethod
    def mask_api_key(api_key_secret: str) -> str:
        if len(api_key_secret) <= 8:
            return "*" * len(api_key_secret)
        return f"{api_key_secret[:4]}***{api_key_secret[-4:]}"
