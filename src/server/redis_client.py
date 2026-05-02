import redis.asyncio as redis
import json
from typing import Any, Optional

from config import config

_redis_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(config.REDIS_URL, decode_responses=True)
    return _redis_pool


async def set_price(price_data: dict):
    r = await get_redis()
    await r.set("current_price", json.dumps(price_data), ex=300)


async def get_price() -> Optional[dict]:
    r = await get_redis()
    data = await r.get("current_price")
    return json.loads(data) if data else None


async def publish(channel: str, message: Any):
    r = await get_redis()
    if not isinstance(message, str):
        message = json.dumps(message, ensure_ascii=False)
    await r.publish(channel, message)
