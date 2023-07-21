import secrets
import warnings
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, BaseSettings, Field, RedisDsn, SecretStr


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
    # Environment name. Used to select the correct environment variables.
    # Possible values: "development", "production".
    env: Literal["development", "staging", "production"] = Field(
        "development",
        env="PYTHON_ENV",
    )

    # URL to the CAS verification server.
    # When a user arrives with a CAS token the backend verifies the token directly with
    # this server.
    cas_server_url: AnyHttpUrl = Field("http://localhost:3004/")

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
    planner_url: AnyHttpUrl = Field("http://localhost:3000")

    # This is the path used in case of prefix stripping (i.e. hosting in /api)
    # This is ignored in development mode for convenience
    root_path: str = "/api"

    # Admin RUT as string. This user will always be the only admin.
    # TODO: Maybe use the username instead of the RUT, because RUTs can have zeros in
    # front of them and this can be confusing.
    # Alternatively, remove leading zeros before matching admin RUTs.
    admin_rut: SecretStr = Field("")

    # JWT secret hex string. If this secret is leaked, anyone can forge JWT tokens for
    # any user.
    # Generate random string by default.
    jwt_secret: SecretStr = Field(default_factory=generate_random_jwt_secret)

    # Algorithm used for JWT secrecy.
    jwt_algorithm: str = "HS256"

    # Time to expire JWT tokens in seconds.
    jwt_expire: float = 18_000

    # Siding SOAP WebService access username.
    # If "", it does not connect to the SIDING webservice and relies solely on the mock
    # responses.
    siding_username: str = ""

    # Siding SOAP WebService access password.
    siding_password: SecretStr = SecretStr("")

    # Siding mock database file.
    # If "", it does not load any mock data.
    # Failing to read the mock database is not a fatal error, only a warning.
    siding_mock_path: Path = Path("../siding-mock-data/data.json")

    # Where to store recorded SIDING responses.
    # If "", responses are not recorded.
    # Steps to record SIDING responses:
    # 1. Set SIDING_RECORD_PATH in the `.env` file to some path
    #   (eg. "./mock-data/siding-mock.json").
    # 2. Run the backend. You may want to clear some caches to force the SIDING
    #   requests to execute and be recorded.
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

    # Whether to resynchronize offer on server startup.
    autosync_offer: bool = True

    # Whether to resynchronize the courseinfo cache on server startup.
    autosync_packedcourses: bool = True

    # URL for the Redis server.
    redis_uri: RedisDsn = Field("redis://localhost:6379")

    # URL for buscacursos-dl, the current temporary catalogo and buscacursos scraper
    # that we use as a courseinfo source.
    buscacursos_dl_url: AnyHttpUrl = Field(
        "https://github.com/negamartin/buscacursos-dl/releases/download/universal-4/coursedata-noprogram.json.xz",
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
settings = Settings(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore
