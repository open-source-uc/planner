import logging
import warnings
from collections.abc import Callable

import limits
from fastapi import Depends, HTTPException, Request

from app.settings import settings
from app.user.auth import require_authentication
from app.user.key import UserKey

LIMIT_REACHED_ERROR = HTTPException(429, detail="Too many requests")

# Note: This uses a synchronous connection pool, which is
# why we cannot use the async pool we create in app.redis
# This plausibly has a performance impact,
# but it is not clear how much.
storage = limits.storage.RedisStorage(str(settings.redis_uri))

# Ping the Redis server to check if it is alive
if not storage.check():
    warnings.warn(
        "Could not connect to Redis, falling back to in-memory storage.",
        stacklevel=1,
    )
    storage = limits.storage.MemoryStorage()
    assert storage.check()


# TODO: Limit nicely in the frontend too.
class Limiter:
    def __init__(self, limit: str) -> None:
        self.limiter = limits.strategies.FixedWindowRateLimiter(storage)
        self.rate = limits.parse(limit)

    def check(self, key: str) -> None:
        if not self.limiter.hit(self.rate, key):
            raise LIMIT_REACHED_ERROR


def ratelimit_guest(limit: str) -> Callable[..., None]:
    """
    Establish a rate limit for guest users, based on IP addresses.

    Example:
    def endpoint(_limited: None = Depends(ratelimit_guest("1/second"))):
        pass

    See https://limits.readthedocs.io/en/latest/quickstart.html#ratelimit-string
    """

    limiter = Limiter(limit)

    def check_limit(request: Request):
        # IMPORTANT: The validity of this depends on
        # a chain of trusted reverse proxy and a properly
        # configured ProxyHeadersMiddleware.
        assert (
            request.client is not None
        ), "Request has no client. This is a security issue."
        logging.debug(f"Checking rate limit for {request.client.host}")
        logging.debug(f"X-Forwarded-For: {request.headers.get('X-Forwarded-For')}")
        limiter.check(request.client.host)

    return check_limit


def ratelimit_user(limit: str) -> Callable[..., UserKey]:
    """
    Establish a rate limit for users, based on RUTs.
    This dependency replaces the `require_authorization` dependency!

    Example:
    def endpoint(user: UserKey = Depends(ratelimit_user("4/3second"))):
        pass

    See https://limits.readthedocs.io/en/latest/quickstart.html#ratelimit-string
    """

    limiter = Limiter(limit)

    def check_limit(user: UserKey = Depends(require_authentication)) -> UserKey:
        limiter.check(user.rut)
        return user

    return check_limit
