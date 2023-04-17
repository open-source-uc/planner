from dataclasses import dataclass
from fastapi import HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Any
from cas import CASClientV3
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
from ..settings import settings
import traceback


# CASClient abuses class constructors (__new__),
# so we are using the versioned class directly
cas_client: CASClientV3 = CASClientV3(
    service_url=settings.login_endpoint,
    server_url=settings.cas_server_url,
)


def generate_token(user: str, rut: str, expire_delta: Optional[float] = None):
    """
    Generate a signed token (one that is unforgeable) with the given user, rut and
    expiration time.
    """
    # Calculate the time that this token expires
    if expire_delta is None:
        expire_delta = settings.jwt_expire
    expire_time = datetime.utcnow() + timedelta(seconds=expire_delta)
    # Pack user, rut and expire date into a signed token
    payload = {"exp": expire_time, "sub": user, "rut": rut}
    token = jwt.encode(
        payload, settings.jwt_secret.get_secret_value(), settings.jwt_algorithm
    )
    return token


def decode_token(token: str):
    """
    Verify a token and extract the user data within it.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret.get_secret_value(), [settings.jwt_algorithm]
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not isinstance(payload["sub"], str):
        raise HTTPException(status_code=401, detail="Invalid token")
    if not isinstance(payload["rut"], str):
        raise HTTPException(status_code=401, detail="Invalid token")

    return UserKey(payload["sub"], payload["rut"])


@dataclass
class UserKey:
    """
    Contains data that identifies a user.
    Holding an instance of this class is intended to mean "I have authorization to
    access data for this user".
    Similarly, requiring this type as an argument is intended to mean "using this
    function requires authorization to access the user".
    """

    user: str
    rut: str


def require_authentication(
    bearer: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
):
    """
    Intended for API endpoints that require authentication.

    Example:
    def endpoint(userdata: UserData = Depends(require_authentication)):
        pass
    """
    return decode_token(bearer.credentials)


async def login_cas(next: Optional[str] = None, ticket: Optional[str] = None):
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
    if ticket:
        # User has just authenticated themselves with CAS, and were redirected here
        # with a token
        if not next:
            return HTTPException(status_code=422, detail="Missing next URL")

        # Verify that the ticket is valid directly with the authority (the CAS server)
        user: Any
        attributes: Any
        _pgtiou: Any
        try:
            user, attributes, _pgtiou = cas_client.verify_ticket(
                ticket
            )  # pyright: reportUnknownMemberType = false
        except Exception:
            traceback.print_exc()
            return HTTPException(status_code=502, detail="Error verifying CAS ticket")

        if not isinstance(user, str) or not isinstance(attributes, dict):
            # Failed to authenticate
            return HTTPException(status_code=401, detail="Authentication failed")

        # Get rut
        rut: Any = attributes["carlicense"]
        if not isinstance(rut, str):
            return HTTPException(
                status_code=500, detail="RUT is missing from CAS attributes"
            )

        # CAS token was validated, generate JWT token
        token = generate_token(user, rut)

        # Redirect to next URL with JWT token attached
        return RedirectResponse(next + f"?token={token}")
    else:
        # User wants to authenticate
        # Redirect to authentication page
        cas_login_url: Any = cas_client.get_login_url()
        if not isinstance(cas_login_url, str):
            return HTTPException(
                status_code=500, detail="CAS redirection URL not found"
            )
        return RedirectResponse(cas_login_url)
