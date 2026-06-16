"""Redis cache and pub/sub service for APA-OS."""

import logging
from typing import Optional
import redis.asyncio as redis
from config import Config

logger = logging.getLogger(__name__)


class RedisService:
    """Redis connection manager."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        self.client = redis.from_url(self.redis_url, decode_responses=True)
        await self.client.ping()
        logger.info(f"Connected to Redis at {self.redis_url}")

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()
            logger.info("Redis connection closed")

    async def health_check(self) -> bool:
        if self.client is None:
            await self.connect()
        try:
            return await self.client.ping()
        except Exception:
            return False


redis_service: Optional[RedisService] = None


def get_redis_service() -> RedisService:
    global redis_service
    if redis_service is None:
        redis_url = getattr(Config, "REDIS_URL", "redis://localhost:6379/0")
        redis_service = RedisService(redis_url)
    return redis_service
