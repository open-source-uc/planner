import contextlib
from typing import Any

from app.settings import settings
from redis.asyncio import ConnectionPool, Redis


def init_redis_pool() -> ConnectionPool:  # type: ignore
    return ConnectionPool.from_url(  # type: ignore
        settings.redis_uri,
        decode_responses=True,
        encoding="utf-8",
    )


connection_pool = init_redis_pool()  # type: ignore


@contextlib.asynccontextmanager
async def get_redis():
    """
    Get a Redis connection from the pool.

    Use with `async with` in order to close the connection at the end of the scope.
    """
    redis: Redis[Any] = Redis(
        connection_pool=connection_pool,  # type: ignore
        auto_close_connection_pool=False,
        decode_responses=True,
        encoding="utf-8",
    )
    try:
        yield redis
    finally:
        await redis.close()
