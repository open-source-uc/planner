import asyncio
import logging
import random
from typing import Literal

import sentry_sdk
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app import routes
from app.database import prisma
from app.logger import setup_logger
from app.redis import get_redis
from app.settings import settings
from app.sync.database import load_packed_data_from_db
from app.sync.siding.client import client as siding_soap_client
from app.sync.siding.client import get_titles


# Set up operation IDs for OpenAPI
def custom_generate_unique_id(route: APIRoute):
    if not route.tags:
        return f"{route.name}"
    return f"{route.tags[0]}-{route.name}"


if settings.env != "development":
    # Runs in staging and production
    sentry_sdk.init(
        dsn="https://618e647e028148928aab01575b19d160@o4505547874172928.ingest.sentry.io/4505547903336448",
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # (We probably want to change this after release to be lower)
        traces_sample_rate=0.5,
        profiles_sample_rate=0.5,
    )
    logging.info("Sentry initialized")

app = FastAPI(
    title="Planner API",
    description="API for the Planner application",
    license_info={
        "name": "GNU Affero General Public License v3.0",
        "identifier": "AGPL-3.0-only",
    },
    generate_unique_id_function=custom_generate_unique_id,
    # Note: In development, always use the proxied root path
    # so you can properly use OpenAPI and Swagger UI.
    # (You can disable it by setting ROOT_PATH as "")
    root_path=settings.root_path,
)

# Set proxy headers
# This is extremely important for security.
# Without this, the backend will implictly trust the IP address of the client
# Important assumptions:
# - All reverse proxies in the chain are trusted
# - The reverse proxy sets the X-Forwarded-For header, discarding untrusted values
# - The reverse proxy sets the X-Forwarded-Proto header, discarding untrusted values
# Our backend is behind Caddy, which does this by default.
# Notably Cloudflare does not strip untrusted values.
# See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For
# and https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#defaults
if settings.env != "development":
    # The trusted hosts imply trust to all the reverse proxies in the chain
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Allow all CORS
# This is OK for production,
# because we want to allow extensions!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "sentry-trace", "baggage"],
)

# Enable compression for large responses
# Lots of JSON in responses, so this saves a lot of space
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.on_event("startup")  # type: ignore
async def startup():
    # Initialize logging
    setup_logger()
    logging.info(f"Starting up worker. Environment: {settings.env}")
    # Connect to database
    await prisma.connect()
    # Setup SIDING webservice
    siding_soap_client.on_startup()
    # HACK: Random sleep to avoid DDoSing the DB
    await asyncio.sleep(random.SystemRandom().random() * 15)
    # Load static data from DB to RAM
    await load_packed_data_from_db()


@app.on_event("shutdown")  # type: ignore
async def shutdown():
    await prisma.disconnect()
    siding_soap_client.on_shutdown()


@app.get("/")
async def root():
    return {"message": "Hello World 👋"}


class HealthResponse(BaseModel):
    detail: dict[str, Literal["unhealthy", "healthy"]] = Field(
        default_factory=lambda: {
            "database": "unhealthy",
            "redis": "unhealthy",
            "sidingOrMock": "unhealthy",
        },
    )


@app.get("/health")
async def health() -> HealthResponse:
    response = HealthResponse()

    try:
        # Check database connection
        await prisma.query_raw("SELECT 1")
        response.detail["database"] = "healthy"
    except Exception as e:  # noqa: BLE001
        logging.error(f"Database error detected: {e}")

    try:
        async with get_redis() as redis:
            # Check Redis connection
            await redis.ping()
            response.detail["redis"] = "healthy"
    except Exception as e:  # noqa: BLE001
        logging.error(f"Redis error detected: {e}")

    try:
        # Check SIDING connection (or its mock)
        await get_titles()
        response.detail["sidingOrMock"] = "healthy"
    except Exception as e:  # noqa: BLE001
        logging.error(f"SIDING error detected: {e}")

    if "unhealthy" in response.detail.values():
        raise HTTPException(
            status_code=500,
            detail=response.detail,
        )
    return response


for router in routes.routers:
    app.include_router(router)
