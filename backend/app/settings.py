import secrets
import warnings
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, BaseSettings, Field, RedisDsn, SecretStr

# Load default and then environment-specific variables
load_dotenv(".env.default", override=False, encoding="utf8")
load_dotenv(".env", override=True, encoding="utf8")


def generate_random_jwt_secret():
    warnings.warn(
        (
            "Using a runtime-generated JWT secret."
            " This won't persist accross starts, please change!"
        ),
        stacklevel=2,
    )
    return secrets.token_hex(64)


class Settings(BaseSettings):
    # NOTE: This class MUST contain production values as defaults.
    # Why? This way we can control most production values through commits, instead
    # of having to manually set them in the production server. The `.env` in production
    # is reserved only for secrets.
    # Also, all env variables required to build containers must be set in `.env.default`

    # Environment name. Used to select the correct environment variables.
    # Possible values: "development", "staging", "production".
    env: Literal["development", "staging", "production"] = Field(
        "production",
        env="PYTHON_ENV",
    )

    # URL to the CAS verification server.
    # When a user arrives with a CAS token the backend verifies the token directly with
    # this server.
    cas_server_url: AnyHttpUrl = Field("https://sso.uc.cl/cas/")

    # URL to the CAS login server.
    # The client's browser is redirected to this URL when they want to log in.
    # If left empty, the same URL as `cas_server_url` is used.
    # If the backend server is in a different network than the client's browser, it may
    # need to use a different address to reach the CAS server.
    cas_login_redirection_url: Literal[""] | AnyHttpUrl = ""

    # URL to the backend endpoint that performs authentication.
    # This URL needs to be whitelisted in the CAS server.
    #
    # Should contain a `next` URL parameter that specifies where to send the
    # authenticated JWT token.
    # In particular, the user browser is redirected to this `next` URL with the JWT
    # token as a query parameter.
    planner_url: AnyHttpUrl = Field("https://mallas.ing.uc.cl")

    # This is the path used in case of prefix stripping (i.e. hosting in /api)
    # This is ignored in development mode for convenience
    root_path: str = "/api"

    # Admin RUT as string. This user will always be the only admin.
    admin_rut: SecretStr = Field("")

    # JWT secret hex string. If this secret is leaked, anyone can forge JWT tokens for
    # any user.
    # Generate random string by default.
    jwt_secret: SecretStr = Field(default_factory=generate_random_jwt_secret)

    # Algorithm used for JWT secrecy.
    jwt_algorithm: str = "HS256"

    # Time to expire JWT tokens in seconds.
    jwt_expire: float = 18_000

    # Siding base URL to patch the SOAP WebService definition with.
    # If "", the app will not attempt to connect to the SIDING webservice at all,
    # relying only on the mock responses.
    siding_host_base: str = ""

    # Siding SOAP WebService access username.
    siding_username: str = ""

    # Siding SOAP WebService access password.
    siding_password: SecretStr = SecretStr("")

    # Siding mock database file.
    # If "", it does not load any mock data.
    # Failing to read the mock database is not a fatal error, only a warning.
    siding_mock_path: Literal[""] | Path = Path("../siding-mock-data/index.json")

    # Where to store recorded SIDING responses.
    # If "", responses are not recorded.
    # Steps to record SIDING responses:
    # 1. Set SIDING_RECORD_PATH in the `.env` file to some path
    #   (eg. "./siding-mock-data/data.json").
    # 2. Run the backend. You may want to reset the database so that the cache is
    #   cleared and it forces the SIDING requests to execute and be recorded.
    # 3. Close the backend **with CTRL+C**.
    #   Force-closing the backend through VSCode will not trigger the shutdown hook to
    #   write the recorded responses.
    # 4. A JSON file will be saved with previous mock data (if any) + the recorded data.
    #   Note that the file may contain sensitive data!
    siding_record_path: Literal[""] | Path = ""

    # Time to expire cached student information in seconds.
    student_info_expire: float = 1800

    # Whether to resynchronize courses on server startup.
    autosync_courses: bool = True

    # Whether to resynchronize curriculums on server startup.
    autosync_curriculums: bool = True

    # URL for the Redis server.
    redis_uri: RedisDsn = Field("redis://redis:6379/0")

    # URL for buscacursos-dl, the current temporary catalogo and buscacursos scraper
    # that we use as a courseinfo source.
    buscacursos_dl_url: AnyHttpUrl = Field(
        "https://github.com/kovaxis/buscacursos-dl/releases/download/universal-5/coursedata.json.xz",
    )

    # Logging level
    log_level: Literal[
        "CRITICAL",
        "ERROR",
        "WARNING",
        "INFO",
        "DEBUG",
    ] = "INFO"

    # Where to store logs (only used in development)
    log_path: Path = Path("logs")


# Load settings and allow global app access to them
# NOTE: Pyright reports this line (rightfully) as an error because there are missing
# arguments.
# However, we actually want this to fail if there are missing environment variables, so
# it's ok to ignore.
settings = Settings()  # type: ignore
