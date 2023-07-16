from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from . import routes, sync
from .database import prisma
from .plan.courseinfo import (
    course_info,
)
from .sync.siding.client import client as siding_soap_client


# Set-up operation IDs for OpenAPI
def custom_generate_unique_id(route: APIRoute):
    if not route.tags:
        return f"{route.name}"
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(generate_unique_id_function=custom_generate_unique_id)

# Allow all CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")  # type: ignore
async def startup():
    await prisma.connect()
    # Setup SIDING webservice
    siding_soap_client.on_startup()
    # Prime course info cache
    courseinfo = await course_info()
    # Sync courses if database is empty
    if len(courseinfo.courses) == 0:
        await sync.run_upstream_sync()
        await course_info()


@app.on_event("shutdown")  # type: ignore
async def shutdown():
    await prisma.disconnect()
    siding_soap_client.on_shutdown()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    # Check database connection
    await prisma.query_raw("SELECT 1")

    return {"message": "OK"}


for router in routes.routers:
    app.include_router(router)
