from __future__ import annotations

from typing import Any

from app.settings import settings
from redis.asyncio import BlockingConnectionPool, Redis


def init_redis_pool() -> BlockingConnectionPool:
    pool: BlockingConnectionPool = BlockingConnectionPool.from_url(  # type: ignore
        settings.redis_uri,
        decode_responses=True,
        encoding="utf-8",
    )
    return pool


connection_pool = init_redis_pool()


# FastAPI dependable for Redis
async def get_redis():
    """
    Get a Redis connection from the pool.
    """
    redis: Redis[Any] = Redis(
        connection_pool=connection_pool,
        auto_close_connection_pool=False,
        decode_responses=True,
        encoding="utf-8",
    )
    try:
        yield redis
    finally:
        await redis.close()
