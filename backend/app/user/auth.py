import contextlib
import traceback
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urljoin

from cas import CASClientV3
from fastapi import Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from prisma.models import AccessLevel as DbAccessLevel
from pydantic import BaseModel

from app.settings import settings
from app.user.key import AdminKey, ModKey, Rut, UserKey

cas_client_store: CASClientV3 | None = None


def _get_service_url(params: dict[str, str]) -> str:
    """
    Get the "CAS service URL" corresponding to this service.

    Example: `https://plan.ing.uc.cl/api/user/login`
    Another example: `https://plan.ing.uc.cl/api/user/login?next=https://plan.ing.uc.cl`

    After the user logs in at the CAS login page, they will be redirected to this URL.
    This URL must be whitelisted in the official CAS server.

    `params` are query parameters to include in the URL.
    """

    # We must import this module inside a function
    # Otherwise we would form an import cycle
    from app.routes.user import router as user_router

    callback_endpoint = "/api" + user_router.url_path_for("authenticate")
    url = urljoin(settings.planner_url, callback_endpoint)

    # Include the `next` parameter to indicate where to redirect after generating the
    # JWT token.
    params["next"] = urljoin(settings.planner_url, "/")

    query_params = urlencode(params)
    return f"{url}?{query_params}"


def _get_cas_client() -> CASClientV3:
    """
    Lazily get the CAS client.

    This must be lazy, because in order to get the service URL we must call
    `_get_service_url`, which imports `app.routes.user`.
    If we imported `app.routes.user` outside of a function, it would cause an import
    loop.
    """
    global cas_client_store
    if cas_client_store is None:
        cas_client_store = CASClientV3(
            service_url=_get_service_url({}),
            server_url=settings.cas_server_url,
        )
    return cas_client_store


def _get_login_url(service_params: dict[str, str]) -> str:
    """
    Get the login URL.
    Redirect the user to this URL to start a CAS login.

    Example: `https://sso.uc.cl/cas/login?service=https://plan.ing.uc.cl/api/user/login?next=https://plan.ing.uc.cl`
    This means:
    1. Go to `sso.uc.cl/cas/login` and let the user enter their username and password.
    2. When done, redirect to `plan.ing.uc.cl/api/user/login` with the CAS token, to
        generate a JWT token.
    3. When the token is generated, redirect to `plan.ing.uc.cl` with the JWT token.

    `service_params` are extra URL parameters to include in step 2.
    """

    # Generate the service URL, including the `next` parameter and any extra parameters
    service_url = _get_service_url(service_params)

    # The base URL for logging in
    # Something like `https://sso.uc.cl/cas`
    cas_login_server = settings.cas_login_redirection_url or settings.cas_server_url
    # The login URL
    # Something like `https://sso.uc.cl/cas/login`
    cas_login_url = urljoin(cas_login_server, "login")
    # The URL parameters to include in the login request
    cas_login_params = urlencode({"service": service_url})
    return f"{cas_login_url}?{cas_login_params}"


async def _is_admin(rut: Rut):
    """
    Checks if user with given RUT is an admin.
    """
    admin = settings.admin_rut.get_secret_value()
    if admin == "":
        return False
    return rut == Rut(admin)


async def _is_mod(rut: Rut):
    """
    Checks if user with given RUT is a mod.
    """
    level = await DbAccessLevel.prisma().find_unique(where={"user_rut": rut})
    if level is None:
        return False
    return level.is_mod


async def allow_force_login(user: UserKey) -> bool:
    """
    Whether to allow a user to log in, even if they are not a valid engineering student.
    """
    return await _is_admin(user.rut) or await _is_mod(user.rut)


async def generate_token(rut: Rut, expire_delta: float | None = None):
    """
    Generate a signed token (one that is unforgeable) with the given rut and
    expiration time.
    """
    # Calculate the time that this token expires
    if expire_delta is None:
        expire_delta = settings.jwt_expire
    expire_time = datetime.now(tz=UTC) + timedelta(seconds=expire_delta)
    # Pack rut and expire date into a signed token
    payload: dict[str, datetime | str | bool] = {
        "exp": expire_time,
        "rut": rut,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        settings.jwt_algorithm,
    )


def decode_token(token: str) -> UserKey:
    """
    Verify a token and extract the user data within it.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            [settings.jwt_algorithm],
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired") from None
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token") from None
    if not isinstance(payload["rut"], str):
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        rut = Rut(payload["rut"])
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e

    return UserKey(rut)


def require_authentication(
    bearer: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> UserKey:
    """
    Intended for API endpoints that requires user authentication.

    Example:
    def endpoint(user_data: UserKey = Depends(require_authentication)):
        pass
    """
    return decode_token(bearer.credentials)


async def require_mod_auth(
    bearer: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> ModKey:
    """
    Intended for API endpoints that requires authentication with mod access.

    Example:
    def endpoint(user_data: ModKey = Depends(require_mod_auth)):
        pass
    """
    key = require_authentication(bearer=bearer)
    if not await _is_mod(key.rut):
        raise HTTPException(status_code=403, detail="Insufficient access")
    return ModKey(key.rut)


async def require_admin_auth(
    bearer: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> AdminKey:
    """
    Intended for API endpoints that requires authentication with admin access.

    Example:
    def endpoint(user_data: AdminKey = Depends(require_admin_auth)):
        pass
    """
    key = require_authentication(bearer=bearer)
    if not await _is_admin(key.rut):
        raise HTTPException(status_code=403, detail="Insufficient access")
    return AdminKey(key.rut)


async def login_cas(
    next: str | None = None,
    ticket: str | None = None,
    impersonate_rut: Rut | None = None,
):
    """
    Login endpoint.
    Has two uses, depending on the presence of `ticket`.

    If `ticket` is not present, then it redirects the browser to the CAS login page.
    This type of requests come from the user browser, who was probably redirected here
    after clicking a "Login" button in the frontend.

    If `ticket` is present, then we assume that the CAS login page redirected the user
    to this endpoint with a token. We verify the token and create a JWT. Then, the
    browser is redirected to the frontend along with this JWT.
    In this case, the frontend URL is whatever the `next` field indicates.
    """
    if ticket is None:
        # User wants to authenticate
        # Redirect to authentication page
        params: dict[str, str] = {}
        if impersonate_rut is not None:
            params["impersonate_rut"] = impersonate_rut
        cas_login_url = _get_login_url(params)
        return RedirectResponse(cas_login_url)

    # User has just authenticated themselves with CAS, and were redirected here
    # with a token
    if not next:
        raise HTTPException(status_code=422, detail="Missing next URL")

    # Verify that the ticket is valid directly with the authority (the CAS server)
    username: Any  # CAS username (ie. mail without @uc.cl)
    attributes: Any  # CAS attributes
    _pgtiou: Any
    try:
        (
            username,
            attributes,
            _pgtiou,
        ) = _get_cas_client().verify_ticket(  # pyright: ignore
            ticket,
        )
    except Exception as e:  # (CAS lib is untyped)
        traceback.print_exc()
        raise HTTPException(status_code=502, detail="Error verifying CAS ticket") from e

    if not isinstance(username, str) or not isinstance(attributes, dict):
        # Failed to authenticate
        raise HTTPException(status_code=401, detail="Authentication failed")

    # Get rut
    rut: Any = None
    with contextlib.suppress(KeyError):
        rut = attributes["carlicense"]
    if not isinstance(rut, str):
        raise HTTPException(
            status_code=500,
            detail="RUT is missing from CAS attributes",
        )
    try:
        rut = Rut(rut)
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail="Received invalid RUT from CAS",
        ) from e

    # Only allow impersonation if the user is a mod
    if impersonate_rut is not None:
        if not await _is_mod(rut):
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        rut = impersonate_rut

    # CAS token was validated, generate JWT token
    token = await generate_token(rut)

    # Redirect to next URL with JWT token attached
    return RedirectResponse(next + f"?token={token}")


class AccessLevelOverview(BaseModel):
    # attributes from db
    name: str = ""
    user_rut: str
    is_mod: bool
    created_at: datetime
    updated_at: datetime
