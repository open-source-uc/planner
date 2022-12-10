from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    # URL to the CAS server endpoint.
    # Used for two purposes:
    # - The user is redirected here when login is required
    # - Tokens are validated directly with this server
    cas_server_url: str = Field(...)

    # URL to the backend endpoint that performs authentication.
    # This URL needs to be whitelisted in the CAS server.
    #
    # Should contain a `next` URL parameter that specifies where to send the
    # authenticated JWT token.
    # In particular, the user browser is redirected to this `next` URL with the JWT
    # token as a query parameter.
    login_endpoint: str = Field(...)

    # JWT secret hex string. If this secret is leaked, anyone can forge JWT tokens for
    # any user.
    jwt_secret: str = Field(...)

    # Algorithm used for JWT secrecy.
    jwt_algorithm: str = "HS256"

    # Time to expire JWT tokens in seconds.
    jwt_expire: int = 18_000


# Load settings and allow global app access to them
settings = Settings()
