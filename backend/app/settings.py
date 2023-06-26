from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseSettings, Field, SecretStr


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

    # Admin RUT as string. This user will always be the only admin.
    # TODO: Maybe use the username instead of the RUT, because RUTs can have zeros in
    # front of them and this can be confusing.
    admin_rut: SecretStr = Field(...)

    # JWT secret hex string. If this secret is leaked, anyone can forge JWT tokens for
    # any user.
    jwt_secret: SecretStr = Field(...)

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
    siding_mock_path: Path = Path("../data/siding-mock.json")

    # Where to store recorded SIDING responses.
    # If "", responses are not recorded.
    # Steps to record SIDING responses:
    # 1. Set SIDING_RECORD_PATH in the `.env` file to some path
    #   (eg. "../data/siding-mock.json").
    # 2. Run the backend. You may want to clear some caches to force the SIDING
    #   requests to execute and be recorded.
    # 3. Close the backend **with CTRL+C**.
    #   Force-closing the backend through VSCode will not trigger the shutdown hook to
    #   write the recorded responses.
    # 4. A JSON file will be saved with previous mock data (if any) + the recorded data.
    #   Note that the file may contain sensitive data!
    siding_record_path: Path = Path("")

    # Time to expire cached student information in seconds.
    student_info_expire: float = 1800


# Make sure the `.env` file is loaded before settings are loaded
load_dotenv()

# Load settings and allow global app access to them
# NOTE: Pyright reports this line (rightfully) as an error because there are missing
# arguments.
# However, we actually want this to fail if there are missing environment variables, so
# it's ok to ignore.
settings = Settings()  # pyright: ignore[reportGeneralTypeIssues]
