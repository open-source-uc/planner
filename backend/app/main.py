from .validate.validate import ValidatablePlan
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from .database import prisma
from prisma.models import Post
from prisma.types import PostCreateInput
from .auth import require_authentication, login_cas, UserData
from .coursesync import run_course_sync
from .validate.rules import clear_course_rules_cache, course_rules
from typing import List, Optional


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
    # Prime course rule cache
    await course_rules()


@app.on_event("shutdown")  # type: ignore
async def shutdown():
    await prisma.disconnect()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    # Check database connection
    await prisma.query_raw("SELECT 1")

    return {"message": "OK"}


@app.get("/posts")
async def get_posts() -> List[Post]:
    return await Post.prisma().find_many()


@app.put("/posts")
async def create_post(post: PostCreateInput):
    return await prisma.post.create(post)


@app.get("/auth/login")
async def authenticate(next: Optional[str] = None, ticket: Optional[str] = None):
    return await login_cas(next, ticket)


@app.get("/auth/check")
async def check_auth(user_data: UserData = Depends(require_authentication)):
    return {"message": "Authenticated"}


@app.post("/sync")
# TODO: Require admin permissions for this endpoint.
async def course_sync():
    await run_course_sync()
    return {
        "message": "Course database updated",
    }


@app.post("/validate/sync")
async def validate_sync():
    clear_course_rules_cache()
    rules = await course_rules()
    return {
        "message": f"Recalculated {len(rules.courses)} course rules",
    }


@app.post("/validate")
async def validate_plan(plan: ValidatablePlan):
    rules = await course_rules()
    diag = plan.diagnose(rules)
    return {"valid": len(diag) == 0, "diagnostic": diag}
