from fastapi import HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Any
from cas import CASClient
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
from .settings import settings


cas_client = CASClient(
    version=3,
    service_url=settings.login_endpoint,
    server_url=settings.cas_server_url,
)


def generate_token(user: str, rut: str, expire_delta: Optional[int] = None):
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
    token = jwt.encode(payload, settings.jwt_secret, settings.jwt_algorithm)
    return token


def decode_token(token: str):
    """
    Verify a token and extract the user data within it.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, [settings.jwt_algorithm])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if type(payload["sub"]) is not str:
        raise HTTPException(status_code=401, detail="Invalid token")
    if type(payload["rut"]) is not str:
        raise HTTPException(status_code=401, detail="Invalid token")
    return UserData(payload["sub"], payload["rut"])


class UserData:
    user: str
    rut: str

    def __init__(self, user: str, rut: str):
        self.user = user
        self.rut = rut


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
    If `ticket` is present, then we assume that the CAS login page redirected the user
    to this endpoint with a token. We verify the token and create a JWT. Then, the
    browser is redirected to the frontend along with this JWT.
    """
    if ticket:
        # User has just authenticated themselves with CAS, and were redirected here
        # with a token
        if not next:
            return HTTPException(status_code=422, detail="Missing next URL")
        # print(f'ticket = "{ticket}"')
        # print(f'next = "{next}"')
        # Verify that ticket is valid directly with CAS server
        user: Any
        attributes: Any
        _pgtiou: Any
        user, attributes, _pgtiou = cas_client.verify_ticket(ticket)
        # print(
        #     "CAS verify response: "
        #     f'user = "{user}", attributes = "{attributes}", pgtiou = "{_pgtiou}"'
        # )
        if not (user and attributes):
            # Failed to authenticate
            return HTTPException(status_code=401, detail="Authentication failed")

        # CAS token was validated, generate JWT token
        token = generate_token(user, attributes["carlicense"])

        # Redirect to next URL with JWT token attached
        return RedirectResponse(next + f"?token={token}")
    else:
        # User wants to authenticate
        # Redirect to authentication page
        cas_login_url: str = cas_client.get_login_url()
        # print(f'cas_login_url = "{cas_login_url}"')
        return RedirectResponse(cas_login_url)
