from collections.abc import Callable

import limits
from fastapi import Depends, HTTPException, Request

from .user.auth import require_authentication
from .user.key import UserKey

LIMIT_REACHED_ERROR = HTTPException(429, detail="Too many requests")

# TODO: Use Redis storage to support multiple instances.
storage = limits.storage.MemoryStorage()


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
        # TODO: If there is any proxy in production between the machine and the
        # internet, requests may all come from the same IP. Check if this is the case.
        limiter.check("" if request.client is None else request.client.host)

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
