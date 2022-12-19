from .validation.curriculum.tree import Curriculum
from .validation.plan import ValidatablePlan, ValidationResult
from .validation.diagnose import diagnose_plan
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from .database import prisma
from prisma.models import Post, Course as DbCourse
from prisma.types import PostCreateInput
from .auth import require_authentication, login_cas, UserData
from .coursesync import run_course_sync
from .validation.courseinfo import clear_course_info_cache, course_info
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
    # Prime course info cache
    await course_info()


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


@app.post("/courses/sync")
# TODO: Require admin permissions for this endpoint.
async def sync_courses():
    await run_course_sync()
    return {
        "message": "Course database updated",
    }


@app.get("/courses/search")
async def search_courses(text: str):
    results = await prisma.query_raw(
        """
        SELECT code, name FROM "Course"
        WHERE code LIKE '%' || $1 || '%'
            OR name LIKE '%' || $1 || '%'
        LIMIT 50
        """,
        text,
    )
    return results


@app.get("/courses")
async def get_course_details(code: str):
    course = await DbCourse.prisma().find_unique(where={"code": code})
    if course is None:
        return HTTPException(status_code=404, detail="Course not found")
    return course


@app.post("/validate/rebuild")
async def rebuild_validation_rules():
    clear_course_info_cache()
    info = await course_info()
    return {
        "message": f"Recached {len(info)} courses",
    }


@app.post("/validate", response_model=ValidationResult)
async def validate_plan(plan: ValidatablePlan, curriculum: Curriculum):
    return await diagnose_plan(plan, curriculum)
