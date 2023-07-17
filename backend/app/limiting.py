from collections.abc import Callable

import limits
from fastapi import Depends, HTTPException, Request

from app.user.auth import require_authentication
from app.user.key import UserKey

LIMIT_REACHED_ERROR = HTTPException(429, detail="Too many requests")

storage = limits.storage.RedisStorage(settings.redis_uri)


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
        # Check for the X-Forwarded-For header, if it exists, use it as the key.
        # Otherwise, use the client IP address.
        # This assumes that the proxy will always set the X-Forwarded-For header
        # and that in development there is no proxy.
        key = request.headers.get("X-Forwarded-For", "")
        if key == "" and request.client:
            key = request.client.host
        limiter.check(key)

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
