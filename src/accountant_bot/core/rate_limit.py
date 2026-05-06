from __future__ import annotations

from datetime import datetime, timezone

import redis.asyncio as redis

from accountant_bot.core.config import Settings


async def allow_ai_request(settings: Settings, user_id: str) -> bool:
    limit = settings.ai_max_requests_per_minute
    if limit <= 0:
        return True
    key = f"ai:rate:{user_id}:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    client = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        value = await client.incr(key)
        if value == 1:
            await client.expire(key, 70)
        return value <= limit
    finally:
        await client.aclose()
